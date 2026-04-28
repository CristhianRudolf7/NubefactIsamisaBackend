-- Tabla de documentos
CREATE TABLE documentos (
    id INT IDENTITY(1,1) PRIMARY KEY,
    tipo_documento INT NOT NULL,  -- 1=Factura, 2=Boleta, 3=NC, 4=ND, 7=Guía
    serie VARCHAR(10) NOT NULL,
    numero INT NOT NULL,
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE,
    moneda VARCHAR(3) DEFAULT 'PEN',  -- PEN, USD
    tipo_cambio DECIMAL(10,4),
    
    -- Datos del cliente
    cliente_tipo_doc INT,  -- 1=DNI, 6=RUC
    cliente_numero_doc VARCHAR(20),
    cliente_denominacion VARCHAR(250),
    cliente_direccion VARCHAR(250),
    cliente_email VARCHAR(100),
    cliente_email_1 VARCHAR(100),
    cliente_email_2 VARCHAR(100),
    
    -- Totales
    porcentaje_igv DECIMAL(5,2) DEFAULT 18.00,
    descuento_global DECIMAL(12,2),
    total_descuento DECIMAL(12,2),
    total_anticipo DECIMAL(12,2),
    total_gravada DECIMAL(12,2),
    total_inafecta DECIMAL(12,2),
    total_exonerada DECIMAL(12,2),
    total_igv DECIMAL(12,2),
    total_gratuita DECIMAL(12,2),
    total_otros_cargos DECIMAL(12,2),
    total DECIMAL(12,2),
    
    -- Percepción/Detracción/Retención
    percepcion_tipo VARCHAR(5),
    percepcion_base DECIMAL(12,2),
    total_percepcion DECIMAL(12,2),
    total_incluido_percepcion DECIMAL(12,2),
    detraccion BIT DEFAULT 0,
    retencion_tipo VARCHAR(5),
    retencion_base DECIMAL(12,2),
    total_retencion DECIMAL(12,2),
    
    -- Estado y respuesta SUNAT
    estado VARCHAR(30) DEFAULT 'pendiente',  -- pendiente, enviado_nubefact, aceptado, aceptado_observaciones, rechazado, anulado
    sunat_transaction INT DEFAULT 1,
    codigo_hash VARCHAR(100),
    cdr VARCHAR(MAX),
    pdf_url VARCHAR(500),
    xml_url VARCHAR(500),
    respuesta_sunat VARCHAR(MAX),
    errores VARCHAR(MAX),
    
    -- Envío al cliente
    enviado_cliente BIT DEFAULT 0,
    fecha_envio_cliente DATETIME,
    
    -- Documento que modifica (para NC/ND)
    documento_modifica_tipo INT,
    documento_modifica_serie VARCHAR(10),
    documento_modifica_numero INT,
    tipo_nota_credito INT,
    tipo_nota_debito INT,
    
    -- Observaciones y datos adicionales
    observaciones VARCHAR(500),
    codigo_unico VARCHAR(50),
    condiciones_pago VARCHAR(100),
    medio_pago VARCHAR(50),
    placa_vehiculo VARCHAR(20),
    orden_compra_servicio VARCHAR(50),
    
    -- Auditoría
    usuario_creacion VARCHAR(100) DEFAULT 'sistema',
    usuario_modificacion VARCHAR(100),
    fecha_creacion DATETIME DEFAULT GETDATE(),
    fecha_modificacion DATETIME,
    fecha_envio_nubefact DATETIME,
    usuario_envio_nubefact VARCHAR(100),
    
    CONSTRAINT UQ_documento UNIQUE (tipo_documento, serie, numero)
);

-- Tabla de items de documentos
CREATE TABLE documentos_items (
    id INT IDENTITY(1,1) PRIMARY KEY,
    documento_id INT NOT NULL FOREIGN KEY REFERENCES documentos(id) ON DELETE CASCADE,
    unidad_medida VARCHAR(10) NOT NULL,  -- NIU, ZZ, etc.
    codigo VARCHAR(50),
    descripcion VARCHAR(500) NOT NULL,
    cantidad DECIMAL(12,4) NOT NULL,
    valor_unitario DECIMAL(12,4),
    precio_unitario DECIMAL(12,4),
    descuento DECIMAL(12,2),
    subtotal DECIMAL(12,2),
    tipo_igv INT DEFAULT 1,  -- 1=Gravado, 2=Exonerado, etc.
    igv DECIMAL(12,2),
    total DECIMAL(12,2),
    anticipo_regularizacion BIT DEFAULT 0,
    anticipo_documento_serie VARCHAR(10),
    anticipo_documento_numero INT,
    codigo_producto_sunat VARCHAR(20),
    orden INT DEFAULT 0
);

-- Tabla de guías de remisión (datos específicos)
CREATE TABLE guias_remision (
    id INT IDENTITY(1,1) PRIMARY KEY,
    documento_id INT NOT NULL FOREIGN KEY REFERENCES documentos(id) ON DELETE CASCADE,
    motivo_traslado VARCHAR(5) NOT NULL,  -- 01=Venta, etc.
    peso_bruto DECIMAL(12,4),
    peso_bruto_unidad VARCHAR(10) DEFAULT 'KGM',
    numero_bultos INT,
    tipo_transporte VARCHAR(5),  -- 01=Público, 02=Privado
    fecha_inicio_traslado DATE,
    
    -- Punto de partida
    punto_partida_ubigeo VARCHAR(10),
    punto_partida_direccion VARCHAR(250),
    punto_partida_codigo_establecimiento VARCHAR(10),
    
    -- Punto de llegada
    punto_llegada_ubigeo VARCHAR(10),
    punto_llegada_direccion VARCHAR(250),
    punto_llegada_codigo_establecimiento VARCHAR(10),
    
    -- Transportista
    transportista_doc_tipo INT,
    transportista_doc_numero VARCHAR(20),
    transportista_denominacion VARCHAR(250),
    transportista_placa VARCHAR(20),
    
    -- Conductor
    conductor_doc_tipo INT,
    conductor_doc_numero VARCHAR(20),
    conductor_nombre VARCHAR(100),
    conductor_apellidos VARCHAR(100),
    conductor_licencia VARCHAR(20)
);

-- Tabla de retenciones (datos específicos)
CREATE TABLE retenciones (
    id INT IDENTITY(1,1) PRIMARY KEY,
    documento_id INT NOT NULL FOREIGN KEY REFERENCES documentos(id) ON DELETE CASCADE,
    retencion_tipo VARCHAR(5),
    retencion_base DECIMAL(12,2),
    porcentaje_retencion DECIMAL(5,2),
    total_retencion DECIMAL(12,2)
);

-- Tabla de auditoría
CREATE TABLE auditoria (
    id INT IDENTITY(1,1) PRIMARY KEY,
    tabla VARCHAR(100) NOT NULL,
    registro_id INT NOT NULL,
    accion VARCHAR(50) NOT NULL,  -- INSERT, UPDATE, DELETE, SEND, CANCEL, etc.
    datos_anteriores NVARCHAR(MAX),
    datos_nuevos NVARCHAR(MAX),
    usuario VARCHAR(100),
    fecha DATETIME DEFAULT GETDATE(),
    ip VARCHAR(50)
);

-- Tabla de configuración
CREATE TABLE configuracion (
    id INT IDENTITY(1,1) PRIMARY KEY,
    clave VARCHAR(100) NOT NULL UNIQUE,
    valor NVARCHAR(MAX),
    descripcion VARCHAR(250),
    fecha_creacion DATETIME DEFAULT GETDATE(),
    fecha_modificacion DATETIME
);

-- Índices para mejorar rendimiento
CREATE INDEX IX_documentos_estado ON documentos(estado);
CREATE INDEX IX_documentos_fecha ON documentos(fecha_emision);
CREATE INDEX IX_documentos_cliente ON documentos(cliente_numero_doc);
CREATE INDEX IX_documentos_items_doc ON documentos_items(documento_id);
CREATE INDEX IX_auditoria_fecha ON auditoria(fecha);
CREATE INDEX IX_auditoria_tabla ON auditoria(tabla, registro_id);

-- Insertar configuración inicial
INSERT INTO configuracion (clave, valor, descripcion) VALUES
('nubefact_ruta', 'https://api.nubefact.com/api/v1/1215c9d4-7765-4ac0-b9ea-268a1ee1b6d1', 'URL de API NubeFact'),
('nubefact_token', '84b1e3cffb89488aab19c0853bc393e23f0f9ff355ef4c44a361a5a702ebedc1', 'Token de autenticación NubeFact'),
('empresa_ruc', '', 'RUC de la empresa'),
('empresa_razon_social', '', 'Razón social de la empresa'),
('empresa_direccion', '', 'Dirección de la empresa');

-- Trigger para auditoría de documentos
CREATE TRIGGER TR_documentos_auditoria
ON documentos
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @accion VARCHAR(50);
    DECLARE @usuario VARCHAR(100);
    
    IF EXISTS (SELECT * FROM inserted) AND EXISTS (SELECT * FROM deleted)
        SET @accion = 'UPDATE';
    ELSE IF EXISTS (SELECT * FROM inserted)
        SET @accion = 'INSERT';
    ELSE
        SET @accion = 'DELETE';
    
    -- Registrar cambios
    IF @accion = 'INSERT'
    BEGIN
        INSERT INTO auditoria (tabla, registro_id, accion, datos_nuevos, usuario)
        SELECT 'documentos', id, @accion, 
               (SELECT * FROM inserted FOR JSON AUTO),
               usuario_creacion
        FROM inserted;
    END
    ELSE IF @accion = 'UPDATE'
    BEGIN
        INSERT INTO auditoria (tabla, registro_id, accion, datos_anteriores, datos_nuevos, usuario)
        SELECT 'documentos', i.id, @accion,
               (SELECT * FROM deleted d WHERE d.id = i.id FOR JSON AUTO),
               (SELECT * FROM inserted ins WHERE ins.id = i.id FOR JSON AUTO),
               i.usuario_modificacion
        FROM inserted i;
    END
    ELSE IF @accion = 'DELETE'
    BEGIN
        INSERT INTO auditoria (tabla, registro_id, accion, datos_anteriores, usuario)
        SELECT 'documentos', id, @accion,
               (SELECT * FROM deleted FOR JSON AUTO),
               'sistema'
        FROM deleted;
    END
END;
