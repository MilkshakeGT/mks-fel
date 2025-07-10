from lxml import etree
import re
import html

def limpiar_descripcion(texto):
    """Limpia el texto para que sea seguro en el campo <Description> del XML FEL"""
    if not texto:
        return ''
    # Eliminar etiquetas HTML si las hay
    texto = re.sub(r'<[^>]+>', '', texto)
    # Reemplazar saltos de línea por espacio
    texto = texto.replace('\n', ' ').replace('\r', ' ')
    # Escapar caracteres especiales XML
    texto = html.escape(texto)
    # Limitar la longitud si es necesario
    return texto #[:250]

def generar_xml_fel(factura):
    """
    Genera el XML requerido por Digifact con los datos de la factura.
    :param factura: recordset de account.move
    :return: XML como string
    """
    root = etree.Element("Root")

    # Versión y país
    etree.SubElement(root, "Version").text = "1.00"
    etree.SubElement(root, "CountryCode").text = "GT"

    # HEADER
    header = etree.SubElement(root, "Header")
    etree.SubElement(header, "DocType").text = "FACT"
    etree.SubElement(header, "IssuedDateTime").text = f"{factura.invoice_date}T08:00:00-06:00"
    etree.SubElement(header, "Currency").text = factura.currency_id.name or "GTQ"

    # SELLER
    company = factura.company_id
    seller = etree.SubElement(root, "Seller")
    etree.SubElement(seller, "TaxID").text = company.vat or ""

    tax_info = etree.SubElement(seller, "TaxIDAdditionalInfo")
    etree.SubElement(tax_info, "Info", Name="AfiliacionIVA", Value="GEN")

    etree.SubElement(seller, "Name").text = company.name or ""

    contact = etree.SubElement(seller, "Contact")
    email_list = etree.SubElement(contact, "EmailList")
    etree.SubElement(email_list, "Email").text = company.email or "info@empresa.com"

    adicional = etree.SubElement(seller, "AdditionlInfo")
    etree.SubElement(adicional, "Info", Name="TipoFrase", Data="1", Value="1")
    etree.SubElement(adicional, "Info", Name="Escenario", Data="1", Value="1")

    branch = etree.SubElement(seller, "BranchInfo")
    etree.SubElement(branch, "Code").text = "1"
    etree.SubElement(branch, "Name").text = company.name or ""

    address_info = etree.SubElement(branch, "AddressInfo")
    etree.SubElement(address_info, "Address").text = company.street or ""
    etree.SubElement(address_info, "City").text = company.zip or "01010"
    etree.SubElement(address_info, "District").text = company.city or "Guatemala"
    etree.SubElement(address_info, "State").text = company.state_id.name or "Guatemala"
    etree.SubElement(address_info, "Country").text = company.country_id.code or "GT"

    # BUYER
    partner = factura.partner_id
    buyer = etree.SubElement(root, "Buyer")
    etree.SubElement(buyer, "TaxID").text = partner.vat or "CF"
    etree.SubElement(buyer, "Name").text = partner.name or "CONSUMIDOR FINAL"

    buyer_contact = etree.SubElement(buyer, "Contact")
    buyer_email_list = etree.SubElement(buyer_contact, "EmailList")
    etree.SubElement(buyer_email_list, "Email").text = partner.email or "cliente@example.com"

    buyer_address_info = etree.SubElement(buyer, "AddressInfo")
    etree.SubElement(buyer_address_info, "Address").text = partner.street or "CIUDAD"
    etree.SubElement(buyer_address_info, "City").text = partner.zip or "01010"
    etree.SubElement(buyer_address_info, "District").text = partner.city or "GUATEMALA"
    etree.SubElement(buyer_address_info, "State").text = partner.state_id.name if partner.state_id else "GUATEMALA"
    etree.SubElement(buyer_address_info, "Country").text = partner.country_id.code if partner.country_id else "GT"

    # ITEMS
    total_impuestos = 0.0
    total_general = 0.0

    items = etree.SubElement(root, "Items")
    for line in factura.invoice_line_ids:
        item = etree.SubElement(items, "Item")

        product_type = "Servicio" if line.product_id.type == 'service' else "Bien"
        etree.SubElement(item, "Type").text = product_type

        etree.SubElement(item, "Description").text = limpiar_descripcion(line.name)
        etree.SubElement(item, "Qty").text = f"{line.quantity:.6f}"
        etree.SubElement(item, "UnitOfMeasure").text = line.product_uom_id.name or "UNI"
        etree.SubElement(item, "Price").text = f"{line.price_unit:.6f}"

        # TAXES
        taxes_node = etree.SubElement(item, "Taxes")
        base = line.price_subtotal
        total = line.price_total
        impuesto = total - base
        total_impuestos += impuesto
        total_general += total

        for tax in line.tax_ids:
            tax_node = etree.SubElement(taxes_node, "Tax")
            etree.SubElement(tax_node, "Code").text = "1"
            etree.SubElement(tax_node, "Description").text = "IVA"
            etree.SubElement(tax_node, "TaxableAmount").text = f"{base:.6f}"
            etree.SubElement(tax_node, "Amount").text = f"{impuesto:.6f}"

        totals_node = etree.SubElement(item, "Totals")
        total_item = line.quantity * line.price_unit
        etree.SubElement(totals_node, "TotalItem").text = f"{total_item:.6f}"

    # TOTALS
    totals = etree.SubElement(root, "Totals")
    total_taxes_elem = etree.SubElement(totals, "TotalTaxes")
    tax_summary = etree.SubElement(total_taxes_elem, "TotalTax")
    etree.SubElement(tax_summary, "Description").text = "IVA"
    etree.SubElement(tax_summary, "Amount").text = f"{total_impuestos:.6f}"

    grand_total = etree.SubElement(totals, "GrandTotal")
    etree.SubElement(grand_total, "InvoiceTotal").text = f"{total_general:.6f}"

    # ADDITIONAL DOCUMENT INFO (ADENDA)
    adenda_info = etree.SubElement(root, "AdditionalDocumentInfo")
    additional = etree.SubElement(adenda_info, "AdditionalInfo")

    # Usa factura.ref si tienes un campo personalizado, o factura.name por defecto
    referencia_interna = factura.ref or factura.name or "SIN_REFERENCIA"
    etree.SubElement(additional, "Code").text = referencia_interna

    return etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True).decode("utf-8")
