from odoo import models, fields, api
from odoo.exceptions import UserError
from ..utils.fel_xml_generator import generar_xml_fel

import requests
import logging
import json

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    fel_uuid = fields.Char(string="Autorización", readonly=True, copy=False)
    serie_fel = fields.Char(string="Serie Documento", readonly=True, copy=False)
    numero_fel = fields.Char(string="Número Documento", readonly=True, copy=False)
    fechaEmision_fel = fields.Char(string="Fecha de emision", readonly=True, copy=False)

    #Cancelación de la FEL
  
    fel_cancelled = fields.Boolean(string="FEL Anulada", default=False)
    fel_cancel_reason = fields.Text(string="Motivo de anulación FEL", default="Error en la factura.")
    fel_cancel_date = fields.Datetime(string="Fecha de anulación FEL")

    show_fel_button = fields.Boolean(string="Mostrar botón FEL", compute="_compute_show_fel_button")

    @api.depends('state', 'fel_uuid', 'move_type')
    def _compute_show_fel_button(self):
        for move in self:
            move.show_fel_button = (
                move.state == 'posted' and
                not move.fel_uuid and
                move.move_type == 'out_invoice'
            )


    def action_certify_fel(self): 

      self.ensure_one()
      _logger.info("Validación: state=%s | move_type=%s | fel_uuid=%s | partner_id=%s | lines=%s",
          self.state, self.move_type, self.fel_uuid, self.partner_id.id if self.partner_id else None, len(self.invoice_line_ids))


      # 🔍 Validaciones previas
      if self.state != 'posted':
          raise UserError("La factura debe estar confirmada para poder certificarla.")

      if self.move_type != 'out_invoice':
          raise UserError("Solo se pueden certificar facturas de cliente.")

      if self.fel_uuid:
          raise UserError("Esta factura ya fue certificada (UUID ya existe).")

      if not self.partner_id:
          raise UserError("Debe seleccionar un cliente para certificar la factura.")

      if not self.invoice_line_ids:
          raise UserError("Debe tener al menos una línea de producto para certificar.")

        # Variables del emisor
      tax_id = '000006792693'
      username = 'GT.000006792693.TESTUSER'
      password = '&2qH?+!?'  # tu clave real
      format = 'XML'
      
      # Test
      url_token = 'https://felgttestaws.digifact.com.gt/gt.com.apinuc/api/login/get_token'
      url_certify = f"https://felgttestaws.digifact.com.gt/gt.com.apinuc/api/v2/transform/nuc?TAXID={tax_id}&USERNAME={username}&FORMAT={format}"
      _logger.info("Url generado:%s", url_certify)
      #Productivo
      # url_token = 'https://felgtaws.digifact.com.gt/gt.com.apinuc/api/login/get_token'
      # url_certify = f"https://felgtaws.digifact.com.gt/gt.com.apinuc/api/v2/transform/nuc?TAXID={tax_id}&USERNAME={username}&FORMAT={format}"

      # Paso 1: Obtener el token
      try:
          response = requests.post(url_token, json={
              'username': username,
              'password': password
          })
          response.raise_for_status()
          token = response.json().get('Token')
          if not token:
              raise UserError("No se obtuvo token de Digifact.")
      except Exception as e:
          raise UserError(f"Error al obtener token: {str(e)}")

      _logger.info("Token obtenido: %s", token)
      
      xml_payload = generar_xml_fel(self)
      _logger.info("📄 XML FEL generado:\n%s", xml_payload)
      # Paso 3: Enviar XML a Digifact
      headers = {
          'Content-Type': 'application/xml',
          'Authorization': token
      }
      
      try:
          response = requests.post(url_certify, headers=headers, data=xml_payload)
          data = response.json()
          if int(data.get("code", 0)) > 1:
            raise UserError(f"Certificación con advertencias o errores: {data.get('message', 'Sin mensaje')}")


          
          uuid_dte = response.json().get('authNumber')
          serie_fel = response.json().get('batch')
          numero_fel = response.json().get('serial')
          fechaEmision_fel = response.json().get('enrolledTimeStamp')
          
          self.fel_uuid = uuid_dte
          self.serie_fel = serie_fel
          self.numero_fel = numero_fel
          self.fechaEmision_fel = fechaEmision_fel
          
          response.raise_for_status()
          # Digifact responde con XML, UUID u otros datos
          _logger.info("Respuesta exitosa : %s",uuid_dte)

      except Exception as e:
          raise UserError(f"Error al certificar con Digifact: {str(e)}")

    def action_cancel_fel(self):
      self.ensure_one()

      _logger.info("Iniciando anulación FEL para factura %s | UUID FEL: %s", self.name, self.fel_uuid)

      if not self.fel_uuid:
          raise UserError("No se puede anular una factura sin UUID FEL.")

      if self.fel_cancelled:
          raise UserError("Esta factura ya fue anulada en FEL.")

      if self.state not in ['cancel', 'draft']:
          raise UserError("La factura debe estar en estado Cancelado o Borrador para anular FEL.")

      # Variables
      tax_id = '000006792693'
      username = 'GT.000006792693.6792693'
      password = 'naPq1w!&'  # tu clave real
      # test
      url_token = 'https://felgttestaws.digifact.com.gt/gt.com.apinuc/api/login/get_token'
      url_cancel = 'https://felgttestaws.digifact.com.gt/gt.com.apinuc/api/CancelFelGT'

      # url_token = 'https://felgtaws.digifact.com.gt/gt.com.apinuc/api/login/get_token'
      # url_cancel = 'https://felgtaws.digifact.com.gt/gt.com.apinuc/api/CancelFelGT'

      # Paso 1: Obtener el token
      try:
          response = requests.post(url_token, json={
              'username': username,
              'password': password
          })
          response.raise_for_status()
          token = response.json().get('Token')
          if not token:
              raise UserError("No se obtuvo token de Digifact.")
      except Exception as e:
          raise UserError(f"Error al obtener token para anulación: {str(e)}")

      _logger.info("Token de anulación obtenido correctamente.")

      # Fecha emisión original → preferible usar fechaEmision_fel si ya la tienes
      if self.fechaEmision_fel:
          fecha_emision = self.fechaEmision_fel  # Usar completa, no modificarla
      else:
          # Si no tienes fechaEmision_fel (cosa rara), puedes usar invoice_date con hora actual
          fecha_emision = fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
      # Payload para CancelFelGT
      payload = {
          "Taxid": tax_id,
          "Autorizacion": self.fel_uuid,
          "IdReceptor": self.partner_id.vat or "CF",
          "FechaEmisionDocumentoAnular": fecha_emision,
          "MotivoAnulacion": self.fel_cancel_reason or "Error en la factura.",
          "Username": username
      }

      headers = {
          'Content-Type': 'application/json',
          'Authorization': token
      }

      # Paso 3: Enviar anulación
      try:
          
          _logger.info("Payload de anulación FEL:\n%s", json.dumps(payload, indent=2, ensure_ascii=False))
          response = requests.post(url_cancel, headers=headers, json=payload)
          response.raise_for_status()

          data = response.json()
          _logger.info("Respuesta de CancelFelGT: %s", data)

          if int(data.get("code", 0)) > 1:
              raise UserError(f"Anulación con advertencias o errores: {data.get('message', 'Sin mensaje')}")

          # Registrar anulación
          self.fel_cancelled = True
          self.fel_cancel_date = fields.Datetime.now()

          _logger.info("Factura %s anulada correctamente en FEL (UUID %s).", self.name, self.fel_uuid)

      except Exception as e:
          _logger.error("Error al anular FEL para factura %s: %s", self.name, str(e))
          raise UserError(f"Error al anular FEL: {str(e)}")
