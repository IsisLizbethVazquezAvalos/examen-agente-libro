import psycopg
from psycopg.rows import dict_row

import os
from dotenv import load_dotenv


class LongTermMemory:

    def __init__(self, database_url: str):
        self.DATABASE_URL = database_url

    # Método para obtener la conexión a la base de datos
    def get_conn(self):
        return psycopg.connect(
            self.DATABASE_URL,
            row_factory=dict_row
        )

    # Método para obtener la memoria a largo plazo
    def get_long_term_memory(self, user_id: str, limit: int = 20):

        with self.get_conn() as conn, conn.cursor() as cur:

            cur.execute(
                """
                SELECT created_at, memory
                FROM public.memoria_largo_plazo
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit)
            )

            return cur.fetchall()

    # Método para insertar memoria
    def insert_long_term_memory(self, user_id: str, memory: str):

        print(
            f"Guardando información del usuario: "
            f"'{user_id}', con memoria '{memory}'"
        )

        if not memory:
            return

        with self.get_conn() as conn, conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO public.memoria_largo_plazo(user_id, memory)
                VALUES (%s, %s)
                """,
                (user_id, memory)
            )

    # Método para formatear la memoria
    def format_memories(self, memories):

        if not memories:
            return ""

        lineas = [
            f"- {m['created_at']}: {m['memory']}\n"
            for m in memories
        ]

        return "".join(lineas)


if __name__ == '__main__':

    load_dotenv()

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "No se encontró DATABASE_URL en el archivo .env"
        )

    ltm = LongTermMemory(database_url)

    # Prueba de inserción
    ltm.insert_long_term_memory(
         "1",
         "Memoria creada desde Python"
     )

    # result = ltm.get_long_term_memory("1")

    # print(ltm.format_memories(result))