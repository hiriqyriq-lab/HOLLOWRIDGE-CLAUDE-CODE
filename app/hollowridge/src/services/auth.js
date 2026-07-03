import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = '@hollowridge_user';

export async function getUser() {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export async function saveUser(user) {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

export async function signOut() {
  await AsyncStorage.removeItem(STORAGE_KEY);
}

// Simulate OTP send — replace with your backend / Twilio / Supabase Auth
export async function sendEmailOTP(email) {
  // TODO: POST to your backend: { email }
  console.log('[auth] send email OTP to', email);
  return { success: true };
}

export async function sendSMSOTP(phone) {
  // TODO: POST to your backend: { phone }
  console.log('[auth] send SMS OTP to', phone);
  return { success: true };
}

export async function verifyOTP(contact, otp) {
  // TODO: verify with backend; return user object on success
  // Stubbed: any 6-digit code passes for dev
  if (otp.length === 6) {
    const user = { contact, verified: true, joinedAt: Date.now() };
    await saveUser(user);
    return { success: true, user };
  }
  return { success: false, error: 'Invalid code' };
}
