# INSTRUCTIVO DE USO — Dashboard SGI Auditoría

## CONPREM GRAU — Prefabricados de Hormigón Limitada

---

## 1. REQUISITOS PREVIOS

### Para acceso Online:
| Requisito | Detalle |
|-----------|---------|
| Navegador web | Chrome, Safari, Firefox o Edge (cualquier versión moderna) |
| Internet | Cualquier conexión |
| Instalación | **No requiere instalar nada** |

### Para acceso Local (opcional):
| Requisito | Detalle |
|-----------|---------|
| Computador | Mac o PC con navegador web |
| Python | Versión 3.11 o superior instalada |
| Conexión | Solo para la primera instalación |

---

## 2. ACCESO AL DASHBOARD

### Opción A — Online (recomendado)

Abra directamente en su navegador:

👉 **https://fafaroster-sgi-dashboard-conprem-srcapp-b0twzg.streamlit.app**

No requiere instalar nada. Funciona desde cualquier computador, tablet o celular con internet.

---

### Opción B — Local (sin internet)

Si prefiere ejecutar el dashboard en su propio computador:

Abra la Terminal y ejecute estos comandos:

```bash
# 1. Ir a la carpeta del dashboard
cd "/Users/rafaelparra/Desktop/DASHBORD INFORME ISO"

# 2. Instalar dependencias
pip3 install -r requirements.txt
```

Si le pide permisos, agregue `--break-system-packages` al final del comando pip.

---

## 3. INICIAR EL DASHBOARD (Solo acceso local)

Si usa la versión local, cada vez que quiera usar el dashboard:

```bash
cd "/Users/rafaelparra/Desktop/DASHBORD INFORME ISO"
PYTHONPATH="." streamlit run src/app.py --server.port 8502
```

Se abrirá automáticamente en su navegador en: **http://localhost:8502**

Para detenerlo, presione `Ctrl + C` en la Terminal.

---

## 4. SECCIONES DEL DASHBOARD

### 4.1 — Resumen Ejecutivo (primera sección visible)

| Elemento | Qué muestra |
|----------|-------------|
| **Total Findings** | Cantidad total de hallazgos únicos de la auditoría |
| **Risk Load Score** | Puntaje ponderado de riesgo total (NCM=5, NCm=2, OdM=1, OBS=0.5) |
| **Compliance Health** | Porcentaje de salud del sistema — cuánto falta para el máximo riesgo |
| **NCM / NCm / ODM / OBS** | Conteo por tipo de hallazgo |
| **Alerta HTS (roja)** | Aparece si existe un hallazgo transversal sistémico |

**Cómo leerlo:** Si Compliance Health está bajo 50%, la situación es crítica. Sobre 70% indica buen avance.

---

### 4.2 — Panel HTS (Hallazgo Transversal Sistémico)

Aparece solo si existe un hallazgo sistémico (NCM-15). Muestra:
- Descripción del hallazgo
- Todas las zonas afectadas (✓ afectada / ✗ no afectada)
- Todas las normas involucradas
- Explicación de por qué es sistémico

---

### 4.3 — Análisis de Pareto

**Gráfico izquierdo — Zonas de Proceso:**
- Las **barras rojas** son las zonas que concentran el 80% del riesgo → prioridad absoluta
- Las **barras verdes** son secundarias
- La **línea amarilla** muestra el % acumulado
- La **línea roja punteada** marca el umbral del 80%

**Gráfico derecho — Cláusulas ISO:**
- Mismo principio pero por cláusula de la norma
- Permite ver qué requisitos específicos de la norma se incumplen más

**Para qué sirve:** Decidir dónde poner los recursos primero. Arreglar las barras rojas elimina el 80% del problema.

---

### 4.4 — Mapa de Calor de Riesgo

Una tabla de colores donde:
- **Filas** = Zonas de proceso (10 zonas)
- **Columnas** = Normas ISO (9001, 14001, 45001)
- **Color** = Intensidad del riesgo (más amarillo/brillante = más riesgo)
- **Número** = Risk Load Score exacto de esa combinación

**Pase el mouse** sobre una celda para ver el desglose (cuántos NCM, NCm, OdM, OBS tiene esa combinación).

---

### 4.5 — Radar de Madurez SGI

Un gráfico tipo "tela de araña" donde:
- Cada eje es una zona de proceso
- La escala va de 0 (peor) a 100 (ningún hallazgo)
- El área coloreada muestra la forma actual del sistema

**Cómo leerlo:** Las zonas donde el radar se hunde hacia el centro son las más débiles. Las que llegan al borde están bien.

---

### 4.6 — Tabla de Hallazgos

Una tabla interactiva con todos los hallazgos. Permite:
- **Ordenar** por cualquier columna (hacer clic en el encabezado)
- **Buscar** usando el campo de búsqueda en el sidebar
- **Ver detalle** haciendo clic en el expansor debajo de la tabla

Columnas: ID | Tipo | Norma | Zona | Cláusula | Descripción (resumida)

---

### 4.7 — Línea de Tiempo (Acciones Correctivas)

Un gráfico Gantt que muestra las acciones correctivas con:
- **Gris** = No iniciado
- **Azul** = En progreso
- **Verde** = Completado
- **Rojo** = Vencido (pasó la fecha límite sin completarse)

Si no hay fechas asignadas todavía, mostrará un mensaje informativo.

---

### 4.8 — Exportar Datos

- **Export CSV:** Descarga un archivo Excel/CSV con todos los hallazgos filtrados
- Los filtros activos se incluyen como metadatos en el archivo

---

## 5. USO DE FILTROS (Sidebar Izquierdo)

Los filtros están en la barra lateral izquierda:

| Filtro | Opciones | Uso |
|--------|----------|-----|
| **ISO Standards** | 9001, 14001, 45001 | Ver solo hallazgos de una norma específica |
| **Finding Types** | NCM, NCm, ODM, OBS | Ver solo un tipo de hallazgo |
| **Process Zones** | Las 10 zonas de la planta | Focalizarse en una zona |
| **Search** | Texto libre | Buscar por palabra clave en descripciones o IDs |

**Reglas de filtrado:**
- Se aplican TODOS los filtros simultáneamente (AND entre categorías)
- Dentro de cada filtro, seleccionar varios valores funciona como OR (ej: seleccionar 9001 + 14001 muestra ambos)
- Para volver a ver todo, seleccione todas las opciones en cada filtro

---

## 6. MÓDULOS ESTRATÉGICOS (Con Clave)

Al final del dashboard hay una sección protegida con clave.

**Clave de acceso:** `conprem2026`

Ingrese la clave una vez y se desbloquean dos pestañas:

### Pestaña 1: Propuesta Técnica-Económica
Muestra la propuesta completa de consultoría dentro del dashboard.

### Pestaña 2: Plan Estratégico SGI
Contiene 4 sub-pestañas:

| Sub-pestaña | Contenido |
|-------------|-----------|
| **Balanced Scorecard** | 4 perspectivas con indicadores gauge (Financiera, Clientes, Procesos, Aprendizaje) + tablas de objetivos |
| **Hoshin Kanri** | Visión estratégica + Objetivos breakthrough + Matriz X de correlación + Cascada organizacional |
| **FODA + Mapa Estratégico** | Análisis Fortalezas/Debilidades/Oportunidades/Amenazas + Diagrama Sankey de causa-efecto |
| **Plan OdM + Roadmap** | Tabla editable de acciones (cambie estado, responsable, plazo) + Timeline 12 meses |

---

## 7. PREGUNTAS FRECUENTES

**¿Se pierden mis cambios si cierro el navegador?**
Los filtros y ediciones en la tabla OdM se reinician al cerrar. Los datos del informe nunca se modifican.

**¿Puedo agregar nuevos hallazgos?**
Sí, editando el archivo `data/informe_hallazgos.md` con el mismo formato de tabla Markdown. El dashboard lo recargará al reiniciar.

**¿Funciona en otro computador?**
Sí. Use la URL online: https://fafaroster-sgi-dashboard-conprem-srcapp-b0twzg.streamlit.app — funciona desde cualquier dispositivo con internet sin instalar nada.

**¿Necesito internet?**
Para la versión online, sí. Para la versión local, solo para la primera instalación (pip install). Después funciona offline.

**¿Puedo cambiar la clave de acceso?**
Sí. Busque `conprem2026` en el archivo `src/app.py` y cámbiela por la clave que prefiera.

---

## 8. SOPORTE

Para soporte técnico o consultas sobre el dashboard:

**Ingeniería & Gestión SpA**

---

*Documento preparado por Ingeniería & Gestión SpA — Junio 2026*
