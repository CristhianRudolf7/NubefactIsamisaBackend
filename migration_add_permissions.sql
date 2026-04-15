-- Migración para agregar campos de permisos granulares a la tabla users
-- Ejecutar este script en SQL Server Management Studio o mediante línea de comandos

USE isamisa_db;
GO

-- Agregar campo puede_acceder_ventas
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'puede_acceder_ventas'
)
BEGIN
    ALTER TABLE users ADD puede_acceder_ventas BIT NOT NULL DEFAULT 0;
    PRINT 'Campo puede_acceder_ventas agregado exitosamente';
END
ELSE
BEGIN
    PRINT 'El campo puede_acceder_ventas ya existe';
END
GO

-- Agregar campo puede_acceder_guias
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'puede_acceder_guias'
)
BEGIN
    ALTER TABLE users ADD puede_acceder_guias BIT NOT NULL DEFAULT 0;
    PRINT 'Campo puede_acceder_guias agregado exitosamente';
END
ELSE
BEGIN
    PRINT 'El campo puede_acceder_guias ya existe';
END
GO

-- Agregar campo puede_acceder_retenciones
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'puede_acceder_retenciones'
)
BEGIN
    ALTER TABLE users ADD puede_acceder_retenciones BIT NOT NULL DEFAULT 0;
    PRINT 'Campo puede_acceder_retenciones agregado exitosamente';
END
ELSE
BEGIN
    PRINT 'El campo puede_acceder_retenciones ya existe';
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
