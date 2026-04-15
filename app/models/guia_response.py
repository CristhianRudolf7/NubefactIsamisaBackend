from sqlalchemy import Column, String, Float, Integer, Text
from ..database import Base


class WHTransactionNube(Base):
    """Modelo para respuestas de NubeFact - Guías de Remisión"""
    __tablename__ = "wh_transaction_nube"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    TransactionId = Column(String(50), index=True)
    serie = Column(String(10))
    numero = Column(String(20))
    enlace = Column(String(500))
    enlace_del_pdf = Column(String(500))
    enlace_del_xml = Column(String(500))
    enlace_del_cdr = Column(String(500))
    aceptada_por_sunat = Column(String(20))
    sunat_description = Column(Text)
    sunat_note = Column(Text)
    sunat_responsecode = Column(String(50))
    sunat_soap_error = Column(Text)
    pdf_zip_base64 = Column(Text)
    xml_zip_base64 = Column(Text)
    cdr_zip_base64 = Column(Text)
    codigo_hash_qr = Column(String(200))
    codigo_hash = Column(String(200))
    error = Column(Text)
    fecha_envio = Column(Float)
    usuario_envio = Column(String(50))
