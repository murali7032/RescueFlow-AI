/**
 * Optional Firebase Auth helper for production builds.
 * Install `firebase` in each app that uses VITE_AUTH_MODE=firebase.
 *
 * Custom claims expected on the ID token:
 *   role: "donor" | "recipient" | "admin"
 *   recipient_id?: number
 *   organization_id?: number
 */

export type FirebaseWebConfig = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  appId?: string;
};

let initPromise: Promise<void> | null = null;

function readConfig(): FirebaseWebConfig | null {
  const env = (import.meta as { env?: Record<string, string | undefined> }).env ?? {};
  if (!env.VITE_FIREBASE_API_KEY || !env.VITE_FIREBASE_PROJECT_ID) {
    return null;
  }
  return {
    apiKey: env.VITE_FIREBASE_API_KEY,
    authDomain: env.VITE_FIREBASE_AUTH_DOMAIN || `${env.VITE_FIREBASE_PROJECT_ID}.firebaseapp.com`,
    projectId: env.VITE_FIREBASE_PROJECT_ID,
    appId: env.VITE_FIREBASE_APP_ID,
  };
}

export function authMode(): "demo" | "firebase" {
  const env = (import.meta as { env?: Record<string, string | undefined> }).env ?? {};
  if (env.VITE_AUTH_MODE === "firebase") return "firebase";
  if (env.VITE_FIREBASE_API_KEY) return "firebase";
  return "demo";
}

async function ensureFirebase(): Promise<typeof import("firebase/auth") | null> {
  const config = readConfig();
  if (!config) return null;

  if (!initPromise) {
    initPromise = (async () => {
      const { initializeApp, getApps } = await import("firebase/app");
      if (!getApps().length) {
        initializeApp(config);
      }
    })();
  }
  await initPromise;
  return import("firebase/auth");
}

/** Returns a Firebase ID token, or null if demo mode / signed out. */
export async function getIdToken(forceRefresh = false): Promise<string | null> {
  if (authMode() !== "firebase") return null;
  const authMod = await ensureFirebase();
  if (!authMod) return null;
  const auth = authMod.getAuth();
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken(forceRefresh);
}

export async function signInWithEmail(email: string, password: string): Promise<void> {
  const authMod = await ensureFirebase();
  if (!authMod) throw new Error("Firebase is not configured");
  await authMod.signInWithEmailAndPassword(authMod.getAuth(), email, password);
}

export async function signOutFirebase(): Promise<void> {
  const authMod = await ensureFirebase();
  if (!authMod) return;
  await authMod.signOut(authMod.getAuth());
}
