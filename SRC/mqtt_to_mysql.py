import json
import logging
import os
import re
import unicodedata

import paho.mqtt.client as mqtt
import pymysql
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("raintrack.mqtt")


def normalize(value):
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return ascii_value.upper()


def normalize_uuid(value):
    return re.sub(r"[^A-Fa-f0-9]", "", str(value or "")).upper()


def validate_data(parameter, value):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    ranges = {"UMIDADE": (0, 100), "HUMIDITY": (0, 100), "TEMPERATURA": (-50, 60), "TEMPERATURE": (-50, 60)}
    limits = ranges.get(normalize(parameter))
    if limits and not limits[0] <= numeric_value <= limits[1]:
        return None
    return numeric_value


def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "raintrack"), password=os.getenv("DB_PASSWORD", ""),
        db=os.getenv("DB_NAME", "rainTrack"), cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4", autocommit=False,
    )


def store_payload(data, connection_factory=get_db_connection):
    station_uuid = normalize_uuid(data.get("uuid"))
    if len(station_uuid) != 12:
        raise ValueError("UUID ausente ou inválido")
    parameters = {key: value for key, value in data.items() if key != "uuid"}
    if not parameters:
        raise ValueError("Mensagem sem medições")

    inserted = 0
    connection = connection_factory()
    try:
        with connection.cursor() as cursor:
            for parameter_name, value in parameters.items():
                normalized_name = normalize(parameter_name)
                valid_value = validate_data(normalized_name, value)
                if valid_value is None:
                    logger.warning("Valor inválido descartado: %s=%r", parameter_name, value)
                    continue
                cursor.execute(
                    """SELECT p.id FROM parameters p
                       JOIN typeParameters t ON p.cdTypeParameter=t.id
                       JOIN stations s ON p.cdStation=s.id
                       WHERE s.uuid=%s AND (UPPER(t.name)=%s OR UPPER(t.typeJson)=%s)""",
                    (station_uuid, normalized_name, normalized_name),
                )
                parameter = cursor.fetchone()
                if not parameter:
                    logger.warning("Parâmetro %s não associado à estação %s", parameter_name, station_uuid)
                    continue
                cursor.execute("INSERT INTO measures (value,cdParameter) VALUES (%s,%s)", (valid_value, parameter["id"]))
                inserted += 1
        connection.commit()
        return inserted
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        topic = os.getenv("MQTT_TOPIC", "raintrack/+/data")
        client.subscribe(topic)
        logger.info("Conectado ao MQTT; ouvindo %s", topic)
    else:
        logger.error("Falha ao conectar ao MQTT: %s", reason_code)


def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        inserted = store_payload(payload)
        logger.info("%d medição(ões) inserida(s) a partir de %s", inserted, message.topic)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        logger.warning("Mensagem inválida em %s: %s", message.topic, error)
    except Exception:
        logger.exception("Erro ao persistir mensagem de %s", message.topic)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=os.getenv("MQTT_CLIENT_ID", "raintrack-consumer"))
    username = os.getenv("MQTT_USERNAME")
    if username:
        client.username_pw_set(username, os.getenv("MQTT_PASSWORD"))
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.connect(os.getenv("MQTT_HOST", "localhost"), int(os.getenv("MQTT_PORT", "1883")), 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
