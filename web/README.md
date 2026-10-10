# Solventa Web

Portal web de **Solventa**, desarrollado con **React, TypeScript y Vite**.

Esta aplicación corresponde al cliente web de la plataforma y permite implementar la experiencia de registro, autenticación y posteriormente los diferentes procesos de gestión de seguros.

Actualmente el frontend incluye la implementación de la **HU19 - Registro, onboarding seguro y autenticación basada en tokens**, con pantallas de inicio de sesión y creación de cuenta integradas con el backend de Solventa.

---

## Tecnologías

El proyecto utiliza:

- **React**
- **TypeScript**
- **Vite**
- **React Router DOM**
- **Vitest**
- **React Testing Library**
- **Testing Library User Event**
- **V8 Coverage**
- **ESLint**

Para el sistema visual se utilizan:

- **Plus Jakarta Sans** para títulos y elementos de jerarquía.
- **DM Sans** para textos descriptivos y ayudas.
- **Material Symbols Outlined** para iconografía.

---

## Sistema visual

El frontend utiliza el sistema visual definido para Solventa.

### Paleta principal

| Uso | Color |
|---|---|
| Noche / estructura principal | `#101B32` |
| Navegación | `#3867F2` |
| Avance / acción principal | `#A7E451` |
| Información | `#29B4D3` |
| Atención | `#F69A4A` |

La interfaz utiliza el color **Noche** para elementos estructurales, **Azul** para navegación y estados de foco, y **Lima** para las acciones principales del usuario.

---

## Funcionalidades implementadas

### Inicio de sesión

Ruta:

```text
/login
```

Permite al usuario:

- Ingresar correo electrónico.
- Ingresar contraseña.
- Consumir el servicio de autenticación del backend.
- Mostrar mensajes de error cuando las credenciales no son válidas.
- Mostrar estado de carga durante el inicio de sesión.
- Redirigir al usuario a `/home` cuando la autenticación es exitosa.
- Navegar hacia la pantalla de creación de cuenta.

Endpoint utilizado:

```http
POST /api/v1/auth/login
```

Ejemplo de solicitud:

```json
{
  "email": "maria.torres@correo.com",
  "password": "Password123!"
}
```

El backend retorna un `access_token` y un `refresh_token`.

---

### Registro de usuario

Ruta:

```text
/registro
```

Permite registrar un nuevo cliente proporcionando:

- Nombre.
- Apellido.
- Correo electrónico.
- Tipo de documento.
- Número de documento.
- Fecha de nacimiento.
- Contraseña.
- Confirmación de contraseña.
- Consentimiento para tratamiento de datos y validación de identidad.

Endpoint utilizado:

```http
POST /api/v1/auth/register
```

Ejemplo:

```json
{
  "nombre": "Maria",
  "apellido": "Torres",
  "email": "maria.torres@correo.com",
  "password": "Password123!",
  "tipo_documento": "CC",
  "numero_documento": "123456789",
  "fecha_nacimiento": "1995-06-15",
  "acepta_validacion_identidad": true
}
```

Durante el registro, el backend realiza la validación de identidad mediante el proveedor KYC configurado.

El frontend valida adicionalmente:

- Contraseña mínima de 8 caracteres.
- Coincidencia entre contraseña y confirmación.
- Autorización de validación de identidad.
- Campos obligatorios.
- Formato válido de correo electrónico.

Cuando el registro finaliza correctamente, se informa al usuario y posteriormente se redirige hacia `/login`.

---

## Integración con el backend

La URL del backend se configura mediante una variable de entorno.

Crear un archivo:

```text
.env
```

con:

```env
VITE_API_URL=http://localhost:8000
```

Existe también:

```text
.env.example
```

como referencia para configurar nuevos ambientes.

El servicio encargado de realizar las llamadas de autenticación se encuentra en:

```text
src/services/auth.service.ts
```

Actualmente expone:

```ts
login()
register()
```

---

## Estructura principal

```text
web/
├── public/
├── src/
│   ├── assets/
│   │
│   ├── components/
│   │   └── auth/
│   │       └── AuthLayout.tsx
│   │
│   ├── pages/
│   │   ├── HomePage.tsx
│   │   ├── LoginPage.tsx
│   │   ├── LoginPage.test.tsx
│   │   ├── RegisterPage.tsx
│   │   └── RegisterPage.test.tsx
│   │
│   ├── services/
│   │   ├── auth.service.ts
│   │   └── auth.service.test.ts
│   │
│   ├── styles/
│   │   └── auth.css
│   │
│   ├── test/
│   │   └── setup.ts
│   │
│   ├── types/
│   │   └── auth.ts
│   │
│   ├── App.tsx
│   ├── index.css
│   └── main.tsx
│
├── .env.example
├── eslint.config.js
├── index.html
├── package.json
├── tsconfig.app.json
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

---

## Componentes principales

### `AuthLayout`

```text
src/components/auth/AuthLayout.tsx
```

Define el layout reutilizable para las pantallas relacionadas con autenticación.

Está compuesto por:

- Panel institucional de Solventa.
- Título y descripción configurables.
- Beneficios del proceso.
- Área destinada al formulario.
- Diseño responsive para dispositivos de menor tamaño.

Es utilizado tanto por:

```text
LoginPage
RegisterPage
```

---

### `LoginPage`

```text
src/pages/LoginPage.tsx
```

Gestiona:

- Estado de correo y contraseña.
- Estado de carga.
- Errores de autenticación.
- Consumo del servicio `login`.
- Redirección posterior al inicio de sesión.

---

### `RegisterPage`

```text
src/pages/RegisterPage.tsx
```

Gestiona:

- Datos personales.
- Datos de identificación.
- Fecha de nacimiento.
- Contraseña.
- Confirmación de contraseña.
- Consentimiento.
- Validaciones del formulario.
- Consumo del servicio `register`.
- Mensajes de éxito y error.
- Redirección al inicio de sesión.

---

### `auth.service`

```text
src/services/auth.service.ts
```

Centraliza el acceso a los endpoints de autenticación del backend.

Esto evita realizar llamadas `fetch` directamente desde las páginas y permite mantener separada la lógica de presentación de la lógica de comunicación HTTP.

---

## Instalación

Se recomienda utilizar **Node.js 20**.

Verificar las versiones:

```bash
node --version
npm --version
```

Instalar las dependencias:

```bash
npm install
```

---

## Ejecutar en desarrollo

Desde la carpeta:

```text
web/
```

ejecutar:

```bash
npm run dev
```

Vite iniciará normalmente el frontend en:

```text
http://localhost:5173
```

La aplicación redirige inicialmente hacia:

```text
http://localhost:5173/login
```

---


## Pruebas

Los tests del frontend utilizan:

- **Vitest**
- **React Testing Library**
- **User Event**
- **jsdom**

Actualmente existen pruebas para:

### Login

- Renderización del formulario.
- Ingreso de credenciales.
- Login exitoso.
- Redirección a `/home`.
- Credenciales incorrectas.
- Manejo de errores inesperados.
- Navegación hacia registro.

### Registro

- Renderización del formulario.
- Validación de contraseña.
- Contraseñas diferentes.
- Consentimiento requerido.
- Cambio del tipo de documento.
- Registro exitoso.
- Manejo de errores retornados por el backend.
- Manejo de errores inesperados.
- Redirección posterior al registro.

### Servicio de autenticación

Se verifica:

- Endpoint utilizado para login.
- Endpoint utilizado para registro.
- Solicitudes HTTP `POST`.
- Serialización del body.
- Errores con `detail`.
- Errores con `detail.mensaje`.
- Errores sin mensaje.
- Respuestas inválidas del servidor.

---

## Ejecutar pruebas

Ejecutar Vitest en modo interactivo:

```bash
npm test
```

Ejecutar los tests una sola vez:

```bash
npm test -- --run
```

Ejecutar tests con cobertura:

```bash
npm test -- --run --coverage
```

El reporte HTML se genera en:

```text
coverage/
```


## Proyecto

**Solventa**  
Proyecto Final — Maestría en Ingeniería de Software  
Universidad de los Andes

**Grupo 11**