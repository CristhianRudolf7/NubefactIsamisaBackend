-- Alterar columna registro_id de INT a VARCHAR para soportar IDs alfanuméricos
-- Ejecutar solo si la columna existe como INT

-- Verificar si es necesario hacer el alter (comentado para ejecución manual)
-- IF EXISTS (
--     SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
--     WHERE TABLE_NAME = 'auditoria' AND COLUMN_NAME = 'registro_id' AND DATA_TYPE = 'int'
-- )
-- BEGIN
--     ALTER TABLE auditoria ALTER COLUMN registro_id VARCHAR(100) NOT NULL;
-- END

-- Ejecutar directamente (SQL Server)
ALTER TABLE auditoria ALTER COLUMN registro_id VARCHAR(100) NOT NULL;
