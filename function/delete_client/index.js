const functions = require('@google-cloud/functions-framework');
const admin = require('firebase-admin');

admin.initializeApp();

// Emails de administradores autorizados (hardcoded)
const ADMIN_EMAILS = [
  'pdtomaestados@gmail.com'
];

functions.http('deleteClient', async (req, res) => {
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
      return res.status(401).json({ error: 'Token de autenticación requerido' });
    }

    const idToken = authHeader.split('Bearer ')[1];
    let decodedToken;
    try {
      decodedToken = await admin.auth().verifyIdToken(idToken);
    } catch (authError) {
      return res.status(401).json({ error: 'Token de autenticación inválido o expirado' });
    }

    const callerEmail = decodedToken.email;
    console.log(`INFO: Solicitud de eliminación por ${callerEmail}`);

    // ── 2. Verificar que el caller es admin ─────────────────────────────
    let isAdmin = ADMIN_EMAILS.includes(callerEmail);

    if (!isAdmin) {
      try {
        const adminDoc = await admin.firestore().collection('Admins').doc(callerEmail).get();
        isAdmin = adminDoc.exists;
      } catch (firestoreError) {
        console.log(`WARN: Error consultando Admins: ${firestoreError.message}`);
      }
    }

    if (!isAdmin) {
      return res.status(403).json({ error: 'No tiene permisos de administrador' });
    }

    // ── 3. Validar parámetros ───────────────────────────────────────────
    const { clienteId } = req.body || {};

    if (!clienteId) {
      return res.status(400).json({ error: 'Falta el parámetro requerido: clienteId' });
    }

    console.log(`INFO: Iniciando eliminación del cliente "${clienteId}"`);

    // ── 4. Obtener el email del cliente desde Firestore ─────────────────
    const clienteDoc = await admin.firestore().collection('Clientes').doc(clienteId).get();
    if (!clienteDoc.exists) {
      return res.status(404).json({ error: `El cliente "${clienteId}" no existe en Firestore` });
    }

    const clienteEmail = clienteDoc.data().email;
    const deleteReport = {
      authDeleted: false,
      localidadesDeleted: 0,
      rutasDeleted: 0,
      usuariosDeleted: 0,
    };

    // ── 5. Eliminar usuario de Firebase Auth ────────────────────────────
    // Solo el Admin SDK puede eliminar cuentas de otros usuarios (no el Client SDK).
    if (clienteEmail) {
      try {
        const userRecord = await admin.auth().getUserByEmail(clienteEmail);
        await admin.auth().deleteUser(userRecord.uid);
        deleteReport.authDeleted = true;
        console.log(`INFO: Usuario de Auth eliminado (uid: ${userRecord.uid})`);
      } catch (authErr) {
        if (authErr.code === 'auth/user-not-found') {
          // El usuario en Auth ya no existía (cuenta huérfana previa), no es un error bloqueante
          console.log(`WARN: Usuario "${clienteEmail}" no encontrado en Auth (posiblemente ya era huérfano). Continuando con limpieza en Firestore.`);
        } else {
          throw authErr;
        }
      }
    }

    // ── 6. Eliminar estructura de Firestore recursivamente ──────────────
    const db = admin.firestore();
    const localidadesRef = db.collection('Clientes').doc(clienteId).collection('Localidades');
    const locSnap = await localidadesRef.get();

    for (const locDoc of locSnap.docs) {
      const locData = locDoc.data();
      const rutas = locData.rutas || [];
      const usuarios = locData.usuarios || [];

      // ── 6a. Borrar subcolección RutaRecorrido de cada ruta y el doc de la Ruta ──
      for (const rRef of rutas) {
        try {
          const rutaPath = rRef.path || rRef;
          const subRef = db.collection(rutaPath).doc().parent;
          // Construir la referencia correctamente desde el path
          const rutaDocRef = db.doc(rutaPath);
          const recorridoRef = rutaDocRef.collection('RutaRecorrido');
          const recorridoSnap = await recorridoRef.get();

          // Borrar en lotes de 400 para no superar el límite de Firestore
          const chunks = [];
          for (let i = 0; i < recorridoSnap.docs.length; i += 400) {
            chunks.push(recorridoSnap.docs.slice(i, i + 400));
          }
          for (const chunk of chunks) {
            const batch = db.batch();
            chunk.forEach(d => batch.delete(d.ref));
            await batch.commit();
          }

          await rutaDocRef.delete();
          deleteReport.rutasDeleted++;
          console.log(`INFO: Ruta eliminada: ${rutaPath}`);
        } catch (rutaErr) {
          console.log(`WARN: Error eliminando ruta ${rRef.path || rRef}: ${rutaErr.message}`);
        }
      }

      // ── 6b. Borrar documentos de Usuarios referenciados ────────────────
      for (const uRef of usuarios) {
        try {
          const usuarioPath = uRef.path || uRef;
          await db.doc(usuarioPath).delete();
          deleteReport.usuariosDeleted++;
          console.log(`INFO: Usuario eliminado: ${usuarioPath}`);
        } catch (uErr) {
          console.log(`WARN: Error eliminando usuario ${uRef.path || uRef}: ${uErr.message}`);
        }
      }

      // ── 6c. Borrar el documento de Localidad ──────────────────────────
      await locDoc.ref.delete();
      deleteReport.localidadesDeleted++;
      console.log(`INFO: Localidad eliminada: ${locDoc.id}`);
    }

    // ── 7. Borrar el documento principal del Cliente ─────────────────────
    await db.collection('Clientes').doc(clienteId).delete();
    console.log(`INFO: Documento Clientes/${clienteId} eliminado de Firestore`);

    // ── 8. Respuesta exitosa ──────────────────────────────────────────────
    return res.status(200).json({
      success: true,
      clienteId,
      report: deleteReport,
    });

  } catch (error) {
    console.error(`ERROR: Error interno al eliminar cliente: ${error.message}`, error);
    return res.status(500).json({
      error: `Error interno: ${error.message}`,
    });
  }
});
