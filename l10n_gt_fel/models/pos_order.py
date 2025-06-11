from odoo import models
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _generate_pos_order_invoice(self):
        res = super()._generate_pos_order_invoice()

        for order in self:
            move = order.account_move
            if move:
                _logger.info("✅ Generada factura para %s: %s", order.name, move.name)
                try:
                    _logger.info("🚀 Llamando a action_certify_fel() desde POS para %s", move.name)
                    move.action_certify_fel()
                    # 🔄 Forzar flush para que todos los campos FEL estén grabados
                    move.flush()
                    self.env.cr.commit()
                except Exception as e:
                    move.message_post(body=f"Error al certificar FEL desde POS: {str(e)}")
                    _logger.error("❌ Error al certificar FEL desde POS: %s", str(e))

        return res
 
