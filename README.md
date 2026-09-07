# 🐎 Sistema de Gestión de Jineteadas

Sistema web desarrollado en **Python + FastAPI** para la administración
integral de campeonatos de jineteadas.

El objetivo es brindar una herramienta moderna, rápida y transparente
para gestionar todo el ciclo de una competencia, desde la organización
del campeonato hasta los resultados finales.

------------------------------------------------------------------------

# 🚀 Estado del proyecto

> **Versión actual:** Desarrollo (rama `develop`)

### Módulos completados

-   ✅ Autenticación
-   ✅ Dashboard
-   ✅ Campeonatos
-   ✅ Fechas
-   ✅ Categorías
-   ✅ Jinetes
-   ✅ Caballos
-   ✅ Tropillas
-   ✅ Inscripciones
-   ✅ QR y acreditación
-   ✅ Sorteos

### Módulos pendientes

-   🏆 Resultados
-   📊 Estadísticas
-   📝 Auditoría completa

------------------------------------------------------------------------

# ✨ Funcionalidades

## Actualmente disponibles

-   🔐 Autenticación de usuarios
-   📋 Dashboard administrativo
-   🏆 Gestión de campeonatos
-   📅 Administración de fechas
-   🏁 Categorías compartidas por campeonato
-   ⚙️ Configuración avanzada de categorías
-   👤 Padrón único de jinetes
-   🔍 Búsqueda de jinetes
-   🐎 Padrón único de caballos
-   🤠 Gestión de tropillas
-   🔗 Asociación de caballos con tropillas
-   🟢 Estados de caballos
-   📥 Modelo e importación masiva de caballos desde Excel
-   🔎 Detección de caballos existentes durante la importación
-   📅 Selección de Fecha + Categoría durante la carga
-   🔒 Una única asignación vigente Fecha + Categoría por caballo
-   🔄 Reasignación manual de caballos
-   ⚡ Reasignación automática cuando corresponde
-   ⚠️ Confirmación de conflictos antes de reasignar
-   🆓 Liberación de caballos de su asignación vigente
-   🔍 Filtros por estado, fecha y categoría
-   📚 Historial de participaciones, reasignaciones y cambios de estado
-   👥 Usuarios con autenticación

## También disponibles

-   📝 Gestión de inscripciones por fecha y categoría
-   📱 Acreditación mediante QR único por jinete
-   📄 Credenciales QR individuales en PDF y descargas masivas
-   🎲 Sorteo transparente por categoría con triple mezcla
-   🐎 Control automático de caballos necesarios y reservas
-   🔢 Asignación automática de orden y palenques
-   💾 Persistencia y consulta de sorteos realizados
-   📄 Generación y reimpresión de PDF de sorteos
-   🌐 Publicación y despublicación de sorteos en frontend público
-   🔁 Eliminación administrativa para permitir resortear
-   🕒 Registro de fecha, hora y usuario del sorteo
-   📝 Auditoría básica de sorteos

## Próximamente

-   🏆 Clasificaciones y resultados
-   📊 Estadísticas
-   📝 Auditoría completa

------------------------------------------------------------------------

# 🛠 Stack tecnológico

-   Python 3.14
-   FastAPI
-   SQLAlchemy 2
-   Alembic
-   SQLite (desarrollo)
-   PostgreSQL (producción)
-   Jinja2
-   Bootstrap 5
-   openpyxl

------------------------------------------------------------------------

# 📂 Arquitectura actual

``` text
Campeonato
│
├── Categorías
│
└── Fechas
      │
      └── Asignación vigente de caballos
            └── Fecha + Categoría

Padrones reutilizables
│
├── Jinetes
├── Caballos
│   └── Historial de participaciones y eventos
└── Tropillas
```

Las **categorías pertenecen al campeonato** y son compartidas por todas
sus fechas.

Los **jinetes, caballos y tropillas** forman padrones reutilizables.

Cada caballo puede tener **una sola asignación vigente** de Fecha +
Categoría. Las asignaciones anteriores, reasignaciones y cambios
relevantes de estado se conservan en su historial.

------------------------------------------------------------------------

# 📂 Estructura del proyecto

``` text
jineteada_26
│
├── app/
│   ├── core/
│   ├── models/
│   ├── routers/
│   ├── services/
│   ├── templates/
│   └── static/
│
├── alembic/
├── backups/
├── data/
├── docs/
├── exports/
├── tests/
│
├── requirements.txt
└── README.md
```

------------------------------------------------------------------------

# 🗺 Roadmap

-   [x] Arquitectura
-   [x] Base de datos
-   [x] Login
-   [x] Dashboard
-   [x] Campeonatos
-   [x] Fechas
-   [x] Categorías
-   [x] Jinetes
-   [x] Caballos
-   [x] Tropillas
-   [x] Inscripciones
-   [x] QR y acreditación
-   [x] Sorteo
-   [x] Reportes PDF de QR y sorteos
-   [x] Publicación pública de sorteos
-   [ ] Resultados
-   [ ] Estadísticas
-   [ ] Auditoría completa

------------------------------------------------------------------------

# 📌 Últimos avances

## Agosto 2026

### ✅ Módulo 6 --- Caballos y Tropillas

**Completado y probado.**

Implementado:

-   [x] Padrón de tropillas.
-   [x] Alta y edición de tropillas.
-   [x] Padrón de caballos.
-   [x] Alta y edición de caballos.
-   [x] Asociación de caballos con tropillas.
-   [x] Estados de caballos: activo, inactivo, lesionado y retirado.
-   [x] Modelo Excel descargable para carga de caballos.
-   [x] Importación masiva de caballos desde Excel.
-   [x] Creación de tropillas durante la importación cuando corresponde.
-   [x] Detección de caballos existentes para evitar duplicados.
-   [x] Selección de Fecha y Categoría durante la importación.
-   [x] Una sola asignación vigente Fecha + Categoría por caballo.
-   [x] Reasignación manual desde la ficha individual.
-   [x] Reasignación automática cuando la asignación anterior
    corresponde a una fecha ya sorteada.
-   [x] Detección de conflictos cuando la asignación anterior todavía no
    puede reemplazarse automáticamente.
-   [x] Pantalla de confirmación mostrando únicamente los caballos
    realmente en conflicto.
-   [x] Liberación inmediata de la asignación vigente.
-   [x] Filtros de caballos por estado, fecha y categoría.
-   [x] Historial permanente de participaciones, reasignaciones y
    cambios de estado.
-   [x] Conservación histórica de estados relevantes como lesiones.
-   [x] Validaciones finales del módulo.

### ✅ Módulo 7 --- Inscripciones, QR y Acreditación

**Completado y probado.**

Implementado:

-   [x] Inscripciones por fecha y categoría.
-   [x] Estados pendiente, validado, ausente y no habilitado.
-   [x] QR único y permanente por jinete.
-   [x] Acreditación mediante lectura QR.
-   [x] Cierre y reapertura controlada de inscripciones.
-   [x] Control de ausencias, suspensiones y descalificaciones.
-   [x] Credencial QR individual en PDF.
-   [x] Descarga masiva de credenciales.

## Septiembre 2026

### ✅ Módulo 8 --- Sorteos

**Implementado y probado.**

Implementado:

-   [x] Preparación por campeonato, fecha y categoría.
-   [x] Resumen de jinetes inscriptos, validados y caballos.
-   [x] Control mínimo de jinetes validados + 2 reservas.
-   [x] Bloqueo cuando faltan caballos.
-   [x] Gestión de caballos excedentes y reservas.
-   [x] Triple mezcla independiente de jinetes y caballos.
-   [x] Asignación automática de orden y palenques 1, 2 y 3.
-   [x] Persistencia y consulta posterior del sorteo.
-   [x] PDF funcional y reimpresión.
-   [x] Publicación y despublicación en frontend público.
-   [x] Eliminación administrativa para permitir resortear.
-   [x] Auditoría básica del sorteo.
-   [x] Horarios en America/Argentina/Buenos_Aires.

### ➡️ Pendiente

Quedan **3 módulos principales**:

1. **Módulo 9 --- Resultados**
2. **Estadísticas**
3. **Auditoría completa**

------------------------------------------------------------------------

# 👨‍💻 Autor

**Lucas Bonfil**

Sistema desarrollado para la administración profesional de campeonatos
de jineteadas, priorizando la transparencia de los sorteos, la
reutilización de datos y la facilidad de uso para organizadores,
secretaría y locución.
