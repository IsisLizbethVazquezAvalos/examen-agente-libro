# Agente Bibliotecario 📚

Práctica 5 de **Inteligencia Artificial – IA Agéntica**: un agente conversacional en Python que responde preguntas sobre libros usando la API gratuita de [Open Library](https://openlibrary.org/developers/api) (sin API key), con *tool calling* y memoria para encadenar preguntas.

## Características

- **2 herramientas (tools)** que el modelo decide cuándo usar:
  | Tool | Endpoint | Retorna |
  |------|----------|---------|
  | `buscar_libro(titulo)` | `GET search.json?q={titulo}` + `authors/{id}.json` | `{"titulo", "autor", "anio", "isbn"}` del primer resultado |
  | `buscar_libros_por_autor(autor)` | `GET search.json?author={autor}` | Lista de 5 títulos (sin repetidos) |
- **Memoria de corto plazo**: historial de la conversación (`SimpleMemory`).
- **Memoria de trabajo**: guarda el último libro consultado (título, autor, año, ISBN) para resolver preguntas como *"¿Qué otros libros tiene ese autor?"*.
- **Memoria de largo plazo (opcional)**: guarda en PostgreSQL/Supabase los libros consultados. Si no hay base de datos, el agente sigue funcionando.
- Modelo LLM: `openai/gpt-oss-120b` vía [Groq](https://console.groq.com/).

## Estructura

```
├── agente1.py              # Agente principal: prompt, definición de TOOLS y ciclo de tool calling
├── libro_tools.py          # Herramientas que consultan Open Library
├── memoria_simple.py       # Memoria de corto plazo (historial)
├── memoria_largo_plazo.py  # Memoria de largo plazo en PostgreSQL
├── requirements.txt
└── .env_example
```

## Instalación

```bash
git clone <url-del-repositorio>
cd examen-agente-libro

python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

Copia el archivo de ejemplo y coloca tus claves:

```bash
# Windows
copy .env_example .env
# Linux / macOS
cp .env_example .env
```

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `API_KEY_GROQ` | Sí | API key de Groq |
| `DATABASE_URL` | No | Conexión PostgreSQL para la memoria de largo plazo |

### (Opcional) Tabla para la memoria de largo plazo

```sql
CREATE TABLE public.memoria_largo_plazo (
    id         BIGSERIAL PRIMARY KEY,
    user_id    TEXT NOT NULL,
    memory     TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## Uso

```bash
python agente1.py
```

Escribe tus preguntas después de `Tú:` y `salir` para terminar. En consola se muestra qué herramienta eligió el modelo y con qué argumentos.

Para probar solo las herramientas, sin el LLM:

```bash
python libro_tools.py
```

## Prueba de la práctica

```
Tú: ¿Quién escribió Cien años de soledad?
[Ronda 1] Herramienta: buscar_libro | Argumentos: {'titulo': 'Cien años de soledad'}
Asistente: El libro Cien años de soledad lo escribió Gabriel García Márquez.

Tú: ¿Qué otros libros tiene ese autor?
[Ronda 1] Herramienta: buscar_libros_por_autor | Argumentos: {'autor': 'Gabriel García Márquez'}
Asistente: Además de Cien años de soledad, Gabriel García Márquez escribió:
- El amor en los tiempos del cólera
- Crónica de una muerte anunciada
- El coronel no tiene quien le escriba
- El general en su laberinto
```

En la segunda pregunta el agente no recibe el nombre del autor: lo toma de la memoria para encadenar la consulta.

## Cómo funciona el tool calling

1. `agente1.py` envía al modelo el prompt del sistema, el historial, la pregunta y la lista `TOOLS`.
2. Si el modelo decide usar una herramienta, responde con `tool_calls` (nombre + argumentos en JSON).
3. `dispatch_tool()` ejecuta la función correspondiente de `LibraryTools`.
4. El resultado se devuelve al modelo como mensaje con rol `tool`, y el modelo redacta la respuesta final.

## Rúbrica

| Criterio | Puntos |
|----------|--------|
| `buscar_libro` | 40 |
| `buscar_libros_por_autor` | 30 |
| Uso de memoria para encadenar | 30 |
