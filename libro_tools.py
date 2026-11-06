import requests


class LibraryTools:
    """Herramientas del agente bibliotecario usando la API gratuita de Open Library."""

    SEARCH_URL = "https://openlibrary.org/search.json"
    AUTHOR_URL = "https://openlibrary.org/authors/{id}.json"

    def _get(self, url: str, params: dict = None):
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _nombre_autor(self, author_id: str):
        """Consulta authors/{id}.json para obtener el nombre oficial del autor."""
        try:
            data = self._get(self.AUTHOR_URL.format(id=author_id))
            return data.get("name")
        except requests.RequestException:
            return None

    def buscar_libro(self, titulo: str):
        """
        GET search.json?q={titulo}
        Retorna {"titulo", "autor", "anio", "isbn"} del primer resultado.
        """
        print(f"Llamando herramienta buscar_libro({titulo})")

        try:
            data = self._get(
                self.SEARCH_URL,
                params={
                    "q": titulo,
                    "limit": 1,
                    "fields": "title,author_name,author_key,first_publish_year,isbn",
                },
            )
        except requests.RequestException as e:
            return {"success": False, "message": f"Error al consultar Open Library: {e}"}

        docs = data.get("docs", [])
        if not docs:
            return {"success": False, "message": f"No se encontró el libro '{titulo}'."}

        libro = docs[0]
        autores = libro.get("author_name") or []
        autor_keys = libro.get("author_key") or []
        isbns = libro.get("isbn") or []

        autor = autores[0] if autores else None
        if autor_keys:
            autor = self._nombre_autor(autor_keys[0]) or autor

        isbn13 = [i for i in isbns if len(i) == 13]
        isbn = isbn13[0] if isbn13 else (isbns[0] if isbns else None)

        return {
            "success": True,
            "titulo": libro.get("title"),
            "autor": autor,
            "anio": libro.get("first_publish_year"),
            "isbn": isbn,
        }

    def buscar_libros_por_autor(self, autor: str):
        """
        GET search.json?author={autor}
        """
        print(f"Llamando herramienta buscar_libros_por_autor({autor})")

        try:
            data = self._get(
                self.SEARCH_URL,
                params={
                    "author": autor,
                    "limit": 20,
                    "fields": "title,first_publish_year",
                },
            )
        except requests.RequestException as e:
            return {"success": False, "message": f"Error al consultar Open Library: {e}"}

        docs = data.get("docs", [])
        if not docs:
            return {"success": False, "message": f"No se encontraron libros de '{autor}'."}

        titulos = []
        vistos = set()
        for doc in docs:
            titulo = doc.get("title")
            if titulo and titulo.lower() not in vistos:
                vistos.add(titulo.lower())
                titulos.append(titulo)
            if len(titulos) == 5:
                break

        return {
            "success": True,
            "autor": autor,
            "titulos": titulos,
        }


if __name__ == "__main__":
    tools = LibraryTools()
    print(tools.buscar_libro("Cien años de soledad"))
    print(tools.buscar_libros_por_autor("Gabriel García Márquez"))
