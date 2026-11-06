from dotenv import load_dotenv
from groq import Groq
import os
import sys
import json

from memoria_simple import SimpleMemory
from memoria_largo_plazo import LongTermMemory
from libro_tools import LibraryTools


sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

client = Groq(api_key=os.environ.get("API_KEY_GROQ"))

memory = SimpleMemory(max_messages=20)

contexto_libro = {}

library_tools = LibraryTools()

long_term_memory = None
database_url = os.environ.get("DATABASE_URL")
if database_url:
    long_term_memory = LongTermMemory(database_url)

USER_ID = "1"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_libro",
            "description": (
                "Busca un libro por su título en Open Library y devuelve "
                "título, autor, año de primera publicación e ISBN del "
                "primer resultado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {
                        "type": "string",
                        "description": "Título del libro a buscar."
                    }
                },
                "required": ["titulo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_libros_por_autor",
            "description": (
                "Busca libros de un autor en Open Library y devuelve una "
                "lista de 5 títulos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "autor": {
                        "type": "string",
                        "description": "Nombre completo del autor."
                    }
                },
                "required": ["autor"]
            }
        }
    }
]


def format_contexto_libro():

    if not contexto_libro:
        return "Aún no se ha consultado ningún libro."

    return (
        f"- Último libro consultado: {contexto_libro.get('titulo')}\n"
        f"- Autor: {contexto_libro.get('autor')}\n"
        f"- Año: {contexto_libro.get('anio')}\n"
        f"- ISBN: {contexto_libro.get('isbn')}"
    )

def create_system_prompt(memories_text):

    return f"""
Eres un agente bibliotecario amigable que habla español y responde
de manera breve y natural.

REGLAS DE LAS HERRAMIENTAS:

- Si el usuario pregunta por un libro (quién lo escribió, en qué año
  se publicó, su ISBN, etc.), utiliza buscar_libro con el título.
- Si el usuario pide libros de un autor, utiliza buscar_libros_por_autor.
- Nunca inventes autores, años, ISBN ni títulos: usa solo lo que
  devuelvan las herramientas.
- Si ocurre un error o no hay resultados, explica qué pasó.

REGLAS DE MEMORIA (ENCADENAR PREGUNTAS):

- Si el usuario se refiere a "ese autor", "el autor", "él", "ella",
  "ese libro", etc., NO le preguntes de quién habla: usa el autor o
  libro guardado en la MEMORIA DE TRABAJO o en la conversación previa.
- Ejemplo: después de "¿Quién escribió <un libro>?", la pregunta
  "¿Qué otros libros tiene ese autor?" debe resolverse llamando a
  buscar_libros_por_autor con el autor recordado.
- Cuando pregunten por "otros libros", omite de la respuesta el libro
  que ya se había consultado.

MEMORIA DE TRABAJO (último libro consultado):

{format_contexto_libro()}

MEMORIAS DE LARGO PLAZO:

== INICIO DE MEMORIAS ==

{memories_text}

== FIN DE MEMORIAS ==
"""


def desactivar_memoria_largo_plazo(error):

    global long_term_memory
    long_term_memory = None
    primera_linea = str(error).splitlines()[0] if str(error) else error
    print(
        "(Memoria de largo plazo desactivada, no se pudo conectar "
        f"a la base de datos: {primera_linea})"
    )


def guardar_memoria_largo_plazo(texto):

    if not long_term_memory:
        return

    try:
        long_term_memory.insert_long_term_memory(USER_ID, texto)
    except Exception as e:
        desactivar_memoria_largo_plazo(e)


def obtener_memorias_largo_plazo():

    if not long_term_memory:
        return ""

    try:
        memories = long_term_memory.get_long_term_memory(USER_ID, limit=20)
        return long_term_memory.format_memories(memories)
    except Exception as e:
        desactivar_memoria_largo_plazo(e)
        return ""



def dispatch_tool(name, args):

    if name == "buscar_libro":
        result = library_tools.buscar_libro(titulo=args["titulo"])

        if result.get("success"):
            contexto_libro.clear()
            contexto_libro.update(
                {k: result[k] for k in ("titulo", "autor", "anio", "isbn")}
            )
            guardar_memoria_largo_plazo(
                f"El usuario consultó el libro '{result['titulo']}' "
                f"de {result['autor']}."
            )

        return result

    if name == "buscar_libros_por_autor":
        return library_tools.buscar_libros_por_autor(autor=args["autor"])

    return {
        "success": False,
        "message": f"Herramienta desconocida: {name}"
    }



def process_response(
    client,
    memory_messages,
    user_text,
    max_tool_rounds=4
):

    memories_text = obtener_memorias_largo_plazo()

   
    messages = [
        {
            "role": "system",
            "content": create_system_prompt(memories_text)
        }
    ] + memory_messages

    messages.append({
        "role": "user",
        "content": user_text
    })

    
    for round_num in range(max_tool_rounds):

        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=TOOLS,
            max_tokens=800
        )

        msg = resp.choices[0].message

      
        if not msg.tool_calls:
            return msg.content or ""

        
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in msg.tool_calls
            ]
        })


        for tool_call in msg.tool_calls:

            name = tool_call.function.name

            args = json.loads(
                tool_call.function.arguments or "{}"
            )

            print(
                f"[Ronda {round_num + 1}] "
                f"Herramienta: {name} | Argumentos: {args}"
            )

            try:
                result = dispatch_tool(name, args)

            except Exception as e:
                result = {
                    "success": False,
                    "message": str(e)
                }

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(
                    result,
                    ensure_ascii=False
                )
            })

    return (
        "Lo siento, tuve problemas para completar "
        "esa solicitud. ¿Puedes reformularla?"
    )


if __name__ == "__main__":

    print("Agente bibliotecario (Open Library) con memoria")
    print("Escribe 'salir' para terminar.\n")

    while True:

        user_input = input("Tú: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ("exit", "salir"):
            print("Hasta luego")
            break

        try:
            assistant_text = process_response(
                client,
                memory.messages(),
                user_input
            )

            print(f"Asistente: {assistant_text}")
            memory.add("user", user_input)
            memory.add("assistant", assistant_text)

        except Exception as e:
            print(f"Error al procesar el mensaje: {e}")
