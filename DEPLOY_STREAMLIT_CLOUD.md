# Guía de Despliegue — Streamlit Cloud

## Pasos para poner el Dashboard online

### Paso 1: Crear cuenta en GitHub (si no tienes)
1. Ve a https://github.com y crea una cuenta gratuita

### Paso 2: Subir el proyecto a GitHub
```bash
cd "/Users/rafaelparra/Desktop/DASHBORD INFORME ISO"

# Inicializar repositorio
git init
git add .
git commit -m "SGI Audit Dashboard - CONPREM GRAU"

# Crear repositorio en GitHub (necesitas GitHub CLI o hacerlo desde la web)
# Opción web: Ve a github.com → New Repository → nombre: sgi-dashboard-conprem
# Luego:
git remote add origin https://github.com/TU_USUARIO/sgi-dashboard-conprem.git
git branch -M main
git push -u origin main
```

### Paso 3: Conectar con Streamlit Cloud
1. Ve a https://share.streamlit.io
2. Inicia sesión con tu cuenta de GitHub
3. Click en "New app"
4. Selecciona:
   - Repository: `TU_USUARIO/sgi-dashboard-conprem`
   - Branch: `main`
   - Main file path: `src/app.py`
5. Click en "Deploy"

### Paso 4: Esperar despliegue (~2-3 minutos)
Streamlit Cloud instalará las dependencias automáticamente desde `requirements.txt`

### Paso 5: Tu URL
Tu dashboard estará disponible en:
**https://tu-usuario-sgi-dashboard-conprem.streamlit.app**

Comparte esta URL con Rodrigo Pinto y cualquier usuario externo.

---

## Configuración necesaria antes de subir

El archivo `.streamlit/config.toml` necesita ajustes para cloud:
- Quitar `port = 8502` (Streamlit Cloud asigna su propio puerto)
- Mantener el tema dark

---

## Privacidad
- El repositorio puede ser **privado** en GitHub (Streamlit Cloud funciona con repos privados)
- La clave `conprem2026` protege los módulos estratégicos
- Cualquiera con la URL puede ver el dashboard público (hallazgos)
- Solo con clave accede a propuesta y plan estratégico
