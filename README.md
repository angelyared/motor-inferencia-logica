# Motor de inferencia lógica

Aplicación web para convertir reglas escritas en español a lógica proposicional y construir un árbol semántico (tableau).

## Ejecutar en Windows

1. Instala Python 3.10 o superior desde https://www.python.org/downloads/
2. Abre la carpeta del proyecto.
3. En la barra de direcciones del Explorador escribe `cmd` y presiona Enter.
4. Ejecuta:

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

5. Se abrirá la aplicación en el navegador.

## Publicar

1. Crea una cuenta o inicia sesión en GitHub.
2. Crea un repositorio público y sube `app.py` y `requirements.txt`.
3. Entra a https://share.streamlit.io/
4. Conecta GitHub, selecciona el repositorio y el archivo `app.py`.
5. Pulsa Deploy. Streamlit generará una URL pública.

## Gramática inicial admitida

- `A y B`
- `A o B`
- `no A`
- `Si A, entonces B`
- `A si y solo si B`

Una regla por línea. Las proposiciones repetidas se reutilizan si su texto es el mismo (ignorando mayúsculas, minúsculas y acentos).

## Nota académica

El analizador es intencionalmente explícito y usa una gramática controlada. Las frases ambiguas o con conectores implícitos deben reformularse. Antes de entregar, hay que probar todos los conectores y revisar los resultados con los ejemplos vistos en clase.
