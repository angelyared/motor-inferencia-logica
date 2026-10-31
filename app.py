
import re
import unicodedata
import streamlit as st
from dataclasses import dataclass, field


# ==========================================
# 1. ANALIZADOR DE LENGUAJE NATURAL
# ==========================================

def limpiar(texto):
    return re.sub(r"\s+", " ", texto.strip().strip(" .;"))


def normalizar(texto):
    texto = limpiar(texto).lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )


def separar_conector(texto, conectores):
    profundidad = 0
    bajo = texto.lower()

    for i in range(len(texto)):

        if texto[i] == "(":
            profundidad += 1
            continue

        if texto[i] == ")":
            profundidad = max(0, profundidad - 1)
            continue

        if profundidad == 0:

            for conector, tipo in conectores:

                if bajo.startswith(conector, i):

                    inicio = texto[:i].strip(" ,")
                    fin = texto[i + len(conector):].strip(" ,")

                    if inicio and fin:
                        return inicio, fin, tipo

    return None


def quitar_parentesis(texto):
    while texto.startswith("(") and texto.endswith(")"):

        profundidad = 0
        exterior = True

        for i, c in enumerate(texto):

            if c == "(":
                profundidad += 1

            elif c == ")":
                profundidad -= 1

            if profundidad == 0 and i < len(texto) - 1:
                exterior = False
                break

        if exterior:
            texto = texto[1:-1].strip()
        else:
            break

    return texto


def analizar(texto):

    texto = quitar_parentesis(limpiar(texto))

    if not texto:
        raise ValueError("Regla vacía.")

    # Bicondicional
    resultado = separar_conector(
        texto,
        [(" si y solo si ", "iff")]
    )

    if resultado:
        a, b, _ = resultado
        return ("iff", analizar(a), analizar(b))

    # Condicional: Si A, entonces B
    coincidencia = re.match(
        r"(?is)^si\s+(.+?)\s*,?\s+entonces\s+(.+)$",
        texto
    )

    if coincidencia:
        a = coincidencia.group(1)
        b = coincidencia.group(2)

        return ("imp", analizar(a), analizar(b))

    # Condicional abreviado: A entonces B
    resultado = separar_conector(
        texto,
        [(" entonces ", "imp")]
    )

    if resultado:
        a, b, _ = resultado
        return ("imp", analizar(a), analizar(b))

    # Disyunción
    resultado = separar_conector(
        texto,
        [(" o ", "or")]
    )

    if resultado:
        a, b, _ = resultado
        return ("or", analizar(a), analizar(b))

    # Conjunción
    resultado = separar_conector(
        texto,
        [(" y ", "and")]
    )

    if resultado:
        a, b, _ = resultado
        return ("and", analizar(a), analizar(b))

    # Negación
    bajo = normalizar(texto)

    if bajo.startswith("no "):
        return ("not", analizar(texto[3:]))

    # Proposición simple
    return ("atom", limpiar(texto))


# ==========================================
# 2. TABLA DE PROPOSICIONES
# ==========================================

def obtener_atomicos(formula, atomos):

    tipo = formula[0]

    if tipo == "atom":

        clave = normalizar(formula[1])

        if clave not in atomos:
            atomos[clave] = formula[1]

    elif tipo == "not":

        obtener_atomicos(formula[1], atomos)

    else:

        obtener_atomicos(formula[1], atomos)
        obtener_atomicos(formula[2], atomos)


def asignar_letras(atomos):

    letras = "pqrstuvwxyzabcdefghijklmno"

    resultado = {}

    for i, clave in enumerate(atomos):

        if i < len(letras):
            resultado[clave] = letras[i]
        else:
            resultado[clave] = f"p{i+1}"

    return resultado


# ==========================================
# 3. CONVERSION A FORMULA LOGICA
# ==========================================

def mostrar_formula(formula, letras, padre=0):

    tipo = formula[0]

    prioridad = {
        "iff": 1,
        "imp": 2,
        "or": 3,
        "and": 4,
        "not": 5,
        "atom": 6
    }

    if tipo == "atom":

        resultado = letras[normalizar(formula[1])]

    elif tipo == "not":

        resultado = "¬" + mostrar_formula(
            formula[1], letras, 5
        )

    else:

        simbolos = {
            "and": " ∧ ",
            "or": " ∨ ",
            "imp": " → ",
            "iff": " ↔ "
        }

        p = prioridad[tipo]

        izquierda = mostrar_formula(
            formula[1], letras, p
        )

        derecha = mostrar_formula(
            formula[2],
            letras,
            p + (1 if tipo == "imp" else 0)
        )

        resultado = izquierda + simbolos[tipo] + derecha

    if prioridad[tipo] < padre:
        return "(" + resultado + ")"

    return resultado


# ==========================================
# 4. TRANSFORMACION A FORMA NORMAL NEGATIVA
# ==========================================

def forma_normal(formula, negacion=False):

    tipo = formula[0]

    if tipo == "atom":

        if negacion:
            return ("not", formula)

        return formula

    if tipo == "not":

        return forma_normal(
            formula[1], not negacion
        )

    if tipo == "and":

        nuevo_tipo = "or" if negacion else "and"

        return (
            nuevo_tipo,
            forma_normal(formula[1], negacion),
            forma_normal(formula[2], negacion)
        )

    if tipo == "or":

        nuevo_tipo = "and" if negacion else "or"

        return (
            nuevo_tipo,
            forma_normal(formula[1], negacion),
            forma_normal(formula[2], negacion)
        )

    if tipo == "imp":

        equivalente = (
            "or",
            ("not", formula[1]),
            formula[2]
        )

        return forma_normal(equivalente, negacion)

    if tipo == "iff":

        equivalente = (
            "and",
            (
                "or",
                ("not", formula[1]),
                formula[2]
            ),
            (
                "or",
                ("not", formula[2]),
                formula[1]
            )
        )

        return forma_normal(equivalente, negacion)

    raise ValueError("Conector desconocido.")


# ==========================================
# 5. MOTOR DE ARBOLES SEMANTICOS
# ==========================================

def es_literal(formula):

    return (
        formula[0] == "atom"
        or (
            formula[0] == "not"
            and formula[1][0] == "atom"
        )
    )


def clave_literal(formula):

    if formula[0] == "atom":
        return normalizar(formula[1]), True

    return normalizar(formula[1][1]), False


def buscar_contradiccion(formulas):

    encontrados = set()

    for formula in formulas:

        if es_literal(formula):

            clave, valor = clave_literal(formula)

            if (clave, not valor) in encontrados:
                return clave

            encontrados.add((clave, valor))

    return None


@dataclass
class Nodo:

    etiqueta: str
    formulas: list = field(default_factory=list)
    estado: str = "abierta"
    hijos: list = field(default_factory=list)


def construir_arbol(formulas, limite=1000):

    contador = [0]

    def expandir(lista):

        contador[0] += 1

        if contador[0] > limite:

            return Nodo(
                "Límite de expansión alcanzado",
                lista,
                "limite"
            )

        contradiccion = buscar_contradiccion(lista)

        if contradiccion:

            return Nodo(
                f"✕ Contradicción: {contradiccion}",
                lista,
                "cerrada"
            )

        indice = next(
            (
                i for i, f in enumerate(lista)
                if not es_literal(f)
            ),
            None
        )

        if indice is None:

            return Nodo(
                "✓ Rama abierta",
                lista,
                "abierta"
            )

        formula = lista[indice]

        restantes = lista[:indice] + lista[indice+1:]

        tipo = formula[0]

        # CONJUNCION: ambas fórmulas en la misma rama

        if tipo == "and":

            nodo = Nodo(
                "∧ Aplicado: ambas fórmulas en la misma rama",
                lista,
                "expandida"
            )

            nodo.hijos = [
                expandir(
                    restantes + [
                        formula[1],
                        formula[2]
                    ]
                )
            ]

            return nodo

        # DISYUNCION: dos ramas

        if tipo == "or":

            nodo = Nodo(
                "∨ Aplicado: división en dos ramas",
                lista,
                "expandida"
            )

            nodo.hijos = [
                expandir(restantes + [formula[1]]),
                expandir(restantes + [formula[2]])
            ]

            return nodo

        return Nodo(
            "Fórmula no desarrollable",
            lista,
            "error"
        )

    raiz = expandir(formulas)

    return raiz, contador[0]


# ==========================================
# 6. RECORRER LAS RAMAS
# ==========================================

def obtener_hojas(nodo):

    if not nodo.hijos:

        yield nodo

    else:

        for hijo in nodo.hijos:
            yield from obtener_hojas(hijo)


def construir_grafo(raiz, letras):

    lineas = [
        "digraph Arbol {",
        'graph [rankdir=TB, bgcolor="transparent"];',
        'node [shape=box, style="rounded,filled", fontname="Arial", fontsize=10];',
        'edge [color="#94a3b8"];'
    ]

    contador = [0]

    def recorrer(nodo, padre=None):

        actual = contador[0]
        contador[0] += 1

        colores = {
            "cerrada": ("#991b1b", "#fee2e2"),
            "abierta": ("#166534", "#dcfce7"),
            "expandida": ("#334155", "#e2e8f0"),
            "limite": ("#92400e", "#fef3c7"),
            "error": ("#991b1b", "#fee2e2")
        }

        borde, fondo = colores[nodo.estado]

        contenido = nodo.etiqueta

        for formula in nodo.formulas[-8:]:

            contenido += "\\n" + mostrar_formula(
                formula, letras
            )

        contenido = contenido.replace('"', "'")

        lineas.append(
            f'n{actual} [label="{contenido}", '
            f'color="{borde}", fillcolor="{fondo}"];'
        )

        if padre is not None:

            lineas.append(
                f"n{padre} -> n{actual};"
            )

        for hijo in nodo.hijos:
            recorrer(hijo, actual)

    recorrer(raiz)

    lineas.append("}")

    return "\n".join(lineas)


# ==========================================
# 7. INTERFAZ WEB
# ==========================================

st.set_page_config(
    page_title="Motor de inferencia lógica",
    page_icon="🌳",
    layout="wide"
)

st.title("🌳 Motor de inferencia lógica")

st.caption(
    "Del lenguaje natural al árbol semántico · Lógica proposicional"
)

st.info(
    "Escribe una regla por línea. "
    "Conectores disponibles: y, o, no, "
    "si... entonces, si y solo si."
)

ejemplo = """Si es de día, entonces voy a trabajar
Si llueve, entonces no voy a trabajar
Es de día"""

entrada = st.text_area(
    "Base de conocimiento",
    value=ejemplo,
    height=150
)

if st.button(
    "Analizar y construir árbol",
    type="primary",
    use_container_width=True
):

    reglas = [
        limpiar(x)
        for x in entrada.splitlines()
        if limpiar(x)
    ]

    if not reglas:

        st.error("Escribe al menos una regla.")

        st.stop()

    try:

        # Interpretar las reglas

        formulas = [
            analizar(regla)
            for regla in reglas
        ]

        # Obtener proposiciones

        atomos = {}

        for formula in formulas:
            obtener_atomicos(formula, atomos)

        letras = asignar_letras(atomos)

        # Tabla de proposiciones

        st.subheader("1. Tabla de proposiciones")

        st.table([
            {
                "Letra": letras[clave],
                "Proposición": significado
            }
            for clave, significado in atomos.items()
        ])

        # Mostrar reglas

        st.subheader("2. Reglas y fórmulas")

        for i, (regla, formula) in enumerate(
            zip(reglas, formulas), 1
        ):

            st.markdown(f"**R{i}:** {regla}")

            st.code(
                f"R{i}: {mostrar_formula(formula, letras)}"
            )

        # Todas las reglas se consideran verdaderas

        iniciales = [
            forma_normal(formula)
            for formula in formulas
        ]

        # Construir árbol

        st.subheader("3. Árbol semántico")

        raiz, cantidad = construir_arbol(iniciales)

        st.graphviz_chart(
            construir_grafo(raiz, letras),
            use_container_width=True
        )

        # Obtener resultados

        hojas = list(obtener_hojas(raiz))

        abiertas = [
            hoja for hoja in hojas
            if hoja.estado == "abierta"
        ]

        cerradas = [
            hoja for hoja in hojas
            if hoja.estado == "cerrada"
        ]

        st.subheader("4. Resultado")

        col1, col2, col3 = st.columns(3)

        col1.metric("Ramas abiertas", len(abiertas))
        col2.metric("Ramas cerradas", len(cerradas))
        col3.metric("Nodos generados", cantidad)

        if abiertas:

            st.success(
                "La base de conocimiento es SATISFACIBLE: "
                "existe al menos una asignación que hace "
                "verdaderas todas las reglas."
            )

            for i, hoja in enumerate(abiertas, 1):

                valores = {}

                for formula in hoja.formulas:

                    if es_literal(formula):

                        clave, valor = clave_literal(formula)

                        valores[clave] = valor

                asignaciones = []

                for clave, significado in atomos.items():

                    valor = valores.get(clave, False)

                    asignaciones.append(
                        f"{letras[clave]} = "
                        f"{'V' if valor else 'F'} "
                        f"({significado})"
                    )

                st.markdown(
                    f"**Modelo de la rama abierta {i}:** "
                    + " · ".join(asignaciones)
                )

        elif len(cerradas) == len(hojas):

            st.error(
                "La base de conocimiento es "
                "INSATISFACIBLE: todas las ramas se cerraron."
            )

        else:

            st.warning(
                "No se pudo completar el árbol. "
                "Se alcanzó el límite de expansión o hubo un error."
            )

        # Desarrollo de ramas

        with st.expander("Ver desarrollo de las ramas"):

            for i, hoja in enumerate(hojas, 1):

                if hoja.estado == "cerrada":
                    estado = "CERRADA ✕"

                elif hoja.estado == "abierta":
                    estado = "ABIERTA ✓"

                else:
                    estado = "INCOMPLETA"

                st.markdown(f"**Rama {i}: {estado}**")

                contenido = [
                    mostrar_formula(f, letras)
                    for f in hoja.formulas
                ]

                st.write(", ".join(contenido))

    except Exception as error:

        st.error(
            f"Error al analizar las reglas: {error}"
        )

        st.warning(
            "Comprueba que cada regla tenga una estructura "
            "clara y que los conectores estén escritos correctamente."
        )

else:

    st.subheader("Vista previa del caso de prueba")

    st.write(
        "El ejemplo ya está escrito. "
        "Pulsa Analizar y construir árbol para ejecutarlo."
    )

st.divider()

st.caption(
    "Proyecto académico de lógica proposicional. "
    "El analizador utiliza una gramática controlada de español."
)
