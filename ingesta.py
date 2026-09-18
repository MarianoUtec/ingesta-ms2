import argparse
import csv
import io
import os
from datetime import date
from pathlib import Path

import boto3
from sqlalchemy import create_engine, text


TABLAS = [
    "aerolinea",
    "aeronave",
    "asiento",
    "empleado",
    "tripulacion",
    "operativo_tierra",
    "vuelo",
    "opera_tripulacion",
]

OUTPUT_LOCAL = Path("output") / "raw" / "ms2"


def get_db_url():
    return (
        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
    )


def get_s3_client():
    # os.getenv devuelve "" cuando la variable viene vacia.
    # Se usa None para permitir que boto3 utilice la cadena
    # de credenciales por defecto, por ejemplo Instance Profile.
    access_key = os.getenv("AWS_ACCESS_KEY_ID") or None
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or None

    return boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=os.getenv("AWS_REGION"),
    )


def extraer_tabla(engine, tabla):
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {tabla}"))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return columns, rows


def escribir_csv_local(tabla, columns, rows):
    fecha = date.today().isoformat()
    outdir = OUTPUT_LOCAL / tabla / fecha
    outdir.mkdir(parents=True, exist_ok=True)
    ruta = outdir / f"{tabla}.csv"

    with ruta.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  {tabla}: {len(rows)} filas -> {ruta}")
    return ruta


def subir_csv_s3(s3, bucket, tabla, columns, rows):
    fecha = date.today().isoformat()
    key = f"raw/ms2/{tabla}/{fecha}/{tabla}.csv"

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )

    print(f"  {tabla}: {len(rows)} filas -> s3://{bucket}/{key}")


def main():
    parser = argparse.ArgumentParser(description="ingesta-ms2: PostgreSQL -> CSV -> S3")
    parser.add_argument("--dry-run", action="store_true", help="lee PostgreSQL y escribe CSVs en output/ sin tocar S3")
    args = parser.parse_args()

    engine = create_engine(get_db_url(), pool_pre_ping=True)

    if args.dry_run:
        print("[ingesta-ms2] Modo: DRY-RUN (local, sin S3)")
        for tabla in TABLAS:
            print(f"Extrayendo {tabla}...")
            columns, rows = extraer_tabla(engine, tabla)
            escribir_csv_local(tabla, columns, rows)
        print("[ingesta-ms2] Completado.")
        return

    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET no configurado (DS-04 pendiente)")

    print(f"[ingesta-ms2] Bucket: {bucket}")
    s3 = get_s3_client()

    for tabla in TABLAS:
        print(f"Extrayendo {tabla}...")
        columns, rows = extraer_tabla(engine, tabla)
        subir_csv_s3(s3, bucket, tabla, columns, rows)

    print("[ingesta-ms2] Completado.")


if __name__ == "__main__":
    main()