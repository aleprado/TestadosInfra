const functions = require('@google-cloud/functions-framework');
const admin = require('firebase-admin');

admin.initializeApp();

// Emails de administradores autorizados (hardcoded)
// También se verifican contra la colección "Admins" de Firestore
const ADMIN_EMAILS = [
  'pdtomaestados@gmail.com'
];

functions.http('createClientAuth', async (req, res) => {
  // ── CORS ──────────────────────────────────────────────────────────────
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.set('Access-Control-Max-Age', '3600');

  if (req.method === 'OPTIONS') {
    return res.status(204).send('');
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Método no permitido. Use POST.' });
  }

  try {
    // ── 1. Verificar token de autenticación ─────────────────────────────
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      console.log('ERROR: Token de autenticación ausente o mal formado');
      return res.status(401).json({ error: 'Token de autenticación requerido (Authorization: Bearer <idToken>)' });
    }

    const idToken = authHeader.split('Bearer ')[1];
    let decodedToken;
    try {
      decodedToken = await admin.auth().verifyIdToken(idToken);
    } catch (authError) {
      console.log(`ERROR: Token inválido: ${authError.message}`);
      return res.status(401).json({ error: 'Token de autenticación inválido o expirado' });
    }

    const callerEmail = decodedToken.email;
    console.log(`INFO: Solicitud de ${callerEmail} (uid: ${decodedToken.uid})`);

    // ── 2. Verificar que el caller es admin ─────────────────────────────
    let isAdmin = ADMIN_EMAILS.includes(callerEmail);

    if (!isAdmin) {
      try {
        const adminDoc = await admin.firestore().collection('Admins').doc(callerEmail).get();
        isAdmin = adminDoc.exists;
      } catch (firestoreError) {
        console.log(`WARN: Error consultando Admins en Firestore: ${firestoreError.message}`);
      }
    }

    if (!isAdmin) {
      console.log(`ERROR: ${callerEmail} no es administrador`);
      return res.status(403).json({ error: 'No tiene permisos de administrador' });
    }

    console.log(`INFO: Admin verificado: ${callerEmail}`);

    // ── 3. Validar parámetros del body ──────────────────────────────────
    const { email, clienteId } = req.body || {};

    if (!email || !clienteId) {
      const missing = [];
      if (!email) missing.push('email');
      if (!clienteId) missing.push('clienteId');
      console.log(`ERROR: Faltan parámetros: ${missing.join(', ')}`);
      return res.status(400).json({
        error: `Faltan parámetros requeridos: ${missing.join(', ')}`,
      });
    }

    console.log(`INFO: Creando cliente "${clienteId}" con email "${email}"`);

    // ── 4. Verificar que clienteId no exista en Firestore ───────────────
    const clienteDoc = await admin.firestore().collection('Clientes').doc(clienteId).get();
    if (clienteDoc.exists) {
      console.log(`ERROR: Cliente "${clienteId}" ya existe en Firestore`);
      return res.status(409).json({
        error: `El cliente "${clienteId}" ya existe en Firestore`,
      });
    }

    // ── 5. Verificar que el email no exista en Firebase Auth ────────────
    try {
      const existingUser = await admin.auth().getUserByEmail(email);
      console.log(`ERROR: Email "${email}" ya registrado (uid: ${existingUser.uid})`);
      return res.status(409).json({
        error: `El email "${email}" ya está registrado en Firebase Auth`,
      });
    } catch (err) {
      if (err.code !== 'auth/user-not-found') {
        throw err;
      }
      // auth/user-not-found → el email no existe, podemos continuar
    }

    // ── 6. Generar contraseña: {clienteId}{4 dígitos random} ────────────
    const randomDigits = Math.floor(1000 + Math.random() * 9000).toString();
    const password = `${clienteId}${randomDigits}`;
    console.log(`INFO: Contraseña generada para "${clienteId}"`);

    // ── 7. Crear usuario en Firebase Auth ───────────────────────────────
    const userRecord = await admin.auth().createUser({
      email: email,
      password: password,
      displayName: clienteId,
    });
    console.log(`INFO: Usuario creado en Auth - uid: ${userRecord.uid}`);

    // ── 8. Crear documento en Firestore: Clientes/{clienteId} ───────────
    await admin.firestore().collection('Clientes').doc(clienteId).set({
      email: email,
    });
    console.log(`INFO: Documento Clientes/${clienteId} creado en Firestore`);

    // ── 9. Respuesta exitosa ────────────────────────────────────────────
    return res.status(200).json({
      success: true,
      uid: userRecord.uid,
      password: password,
    });

  } catch (error) {
    console.error(`ERROR: Error interno: ${error.message}`, error);
    return res.status(500).json({
      error: `Error interno: ${error.message}`,
    });
  }
});
