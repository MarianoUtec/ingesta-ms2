# ingesta-ms2

Servicio de ingesta de MS2.

Extrae el 100% de las tablas de PostgreSQL de MS2 y las
carga como archivos CSV en Amazon S3 para su posterior
procesamiento mediante AWS Glue y Amazon Athena.

## Arquitectura

```text
PostgreSQL MS2
      |
      | SELECT * FROM tabla
      v
 ingesta-ms2
 Docker + Python
      |
      | CSV
      v
 Amazon S3
      |
      v
raw/ms2/<tabla>/<fecha>/<tabla>.csv
      |
      v
 AWS Glue
      |
      v
 Amazon Athena

## Tablas

- aerolinea
- aeronave
- asiento
- empleado
- tripulacion
- operativo_tierra
- vuelo
- opera_tripulacion