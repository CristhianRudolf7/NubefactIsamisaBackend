-- Migración para agregar campos celular y recibir_notificaciones a la tabla users
-- Ejecutar este script en SQL Server Management Studio o mediante línea de comandos

USE isamisa_db;
GO

-- Agregar campo celular
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'celular'
)
BEGIN
    ALTER TABLE users ADD celular VARCHAR(9) NOT NULL DEFAULT '000000000';
    PRINT 'Campo celular agregado exitosamente';
END
ELSE
BEGIN
    PRINT 'El campo celular ya existe';
END
GO

-- Agregar campo recibir_notificaciones
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'recibir_notificaciones'
)
BEGIN
    ALTER TABLE users ADD recibir_notificaciones BIT NOT NULL DEFAULT 1;
    PRINT 'Campo recibir_notificaciones agregado exitosamente';
END
ELSE
BEGIN
    PRINT 'El campo recibir_notificaciones ya existe';
END
GO

-- Verificar la estructura de la tabla
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'users'
ORDER BY ORDINAL_POSITION;
GO

PRINT 'Migración completada exitosamente';
GO
