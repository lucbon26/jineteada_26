# 🐎 Sistema de Gestión de Jineteadas

Sistema web desarrollado en **Python + FastAPI** para la administración integral de campeonatos de jineteadas.

El objetivo es brindar una herramienta moderna, rápida y transparente para gestionar todo el ciclo de una competencia, desde la organización del campeonato hasta los resultados finales.

---

# 🚀 Estado del proyecto

> **Versión actual:** Desarrollo (rama `develop`)

### Módulos completados

- ✅ Autenticación
- ✅ Dashboard
- ✅ Campeonatos
- ✅ Fechas
- ✅ Categorías
- ✅ Jinetes

### Próximos módulos

- 🐎 Caballos
- 🤠 Tropillas
- 📝 Inscripciones
- 🎲 Sorteo
- 🏆 Resultados
- 📄 Reportes PDF
- 📊 Estadísticas
- 📝 Auditoría

---

# ✨ Funcionalidades

## Actualmente disponibles

- 🔐 Autenticación de usuarios
- 📋 Dashboard administrativo
- 🏆 Gestión de campeonatos
- 📅 Administración de fechas
- 🏁 Categorías compartidas por campeonato
- ⚙ Configuración avanzada de categorías
- 👤 Padrón de jinetes
- 🔍 Búsqueda de jinetes
- 👥 Usuarios con autenticación

## Próximamente

- 🐎 Gestión de caballos
- 🤠 Gestión de tropillas
- 📥 Importación masiva desde Excel
- 📱 Confirmación mediante QR
- 🎲 Sorteo transparente
- 📄 Generación automática de PDF
- 🏆 Clasificaciones
- 📊 Estadísticas
- 📝 Auditoría completa

---

# 🛠 Stack tecnológico

- Python 3.14
- FastAPI
- SQLAlchemy 2
- Alembic
- SQLite (desarrollo)
- PostgreSQL (producción)
- Jinja2
- Bootstrap 5

---

# 📂 Arquitectura actual

```
Campeonato
│
├── Categorías
│
├── Fechas
│
└── (próximamente)
      ├── Caballos
      ├── Tropillas
      ├── Inscripciones
      ├── Sorteo
      └── Resultados
```

Las **categorías pertenecen al campeonato** y son compartidas por todas sus fechas.

Los **jinetes** forman un padrón único reutilizable entre campeonatos.

---

# 📂 Estructura del proyecto

```text
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

---

# 🗺 Roadmap

- [x] Arquitectura
- [x] Base de datos
- [x] Login
- [x] Dashboard
- [x] Campeonatos
- [x] Fechas
- [x] Categorías
- [x] Jinetes
- [ ] Caballos
- [ ] Tropillas
- [ ] Inscripciones
- [ ] QR
- [ ] Sorteo
- [ ] Resultados
- [ ] Reportes PDF
- [ ] Estadísticas
- [ ] Auditoría

---

## 📌 Últimos avances

### Agosto 2026

### ✅ Módulo 5 — Jinetes

Gestión general del padrón de jinetes.

Implementado:

- Alta de jinetes.
- Listado general.
- Búsqueda por nombre, apellido, DNI o localidad.
- Filtro por estado.
- Ficha individual del jinete.
- Edición de datos personales y de contacto.
- Validación de DNI único.
- Estados:
  - Activo.
  - Inactivo.
  - Suspendido.
  - Descalificado.
- Integración con el menú principal y navegación del sistema.
---

# 👨‍💻 Autor

**Lucas Bonfil**

Sistema desarrollado para la administración profesional de campeonatos de jineteadas, priorizando la transparencia de los sorteos, la reutilización de datos y la facilidad de uso para organizadores, secretaría y locución.