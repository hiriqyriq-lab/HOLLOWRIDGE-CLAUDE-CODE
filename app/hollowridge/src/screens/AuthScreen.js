import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ActivityIndicator, ScrollView,
} from 'react-native';
import { colors, fonts, spacing } from '../theme';
import { sendEmailOTP, sendSMSOTP, verifyOTP } from '../services/auth';

const STEPS = { METHOD: 'method', CONTACT: 'contact', OTP: 'otp' };

export default function AuthScreen({ onAuthed }) {
  const [step, setStep] = useState(STEPS.METHOD);
  const [method, setMethod] = useState(null); // 'email' | 'sms'
  const [contact, setContact] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSend() {
    setError('');
    if (!contact.trim()) { setError('Enter your ' + (method === 'email' ? 'email' : 'phone number')); return; }
    setLoading(true);
    const res = method === 'email'
      ? await sendEmailOTP(contact.trim().toLowerCase())
      : await sendSMSOTP(contact.trim());
    setLoading(false);
    if (res.success) setStep(STEPS.OTP);
    else setError(res.error || 'Failed to send code.');
  }

  async function handleVerify() {
    setError('');
    if (otp.length !== 6) { setError('Enter the 6-digit code'); return; }
    setLoading(true);
    const res = await verifyOTP(contact.trim(), otp.trim());
    setLoading(false);
    if (res.success) onAuthed(res.user);
    else setError(res.error || 'Invalid code.');
  }

  return (
    <KeyboardAvoidingView style={s.root} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={s.inner} keyboardShouldPersistTaps="handled">

        <Text style={s.wordmark}>HOLLOW RIDGE</Text>
        <Text style={s.sub}>PEAK PIONEER ACCESS</Text>

        {step === STEPS.METHOD && (
          <>
            <Text style={s.label}>Choose your sign-in method</Text>
            <TouchableOpacity style={[s.methodBtn, method === 'email' && s.methodBtnActive]}
              onPress={() => { setMethod('email'); setStep(STEPS.CONTACT); }}>
              <Text style={s.methodText}>✉  EMAIL</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[s.methodBtn, method === 'sms' && s.methodBtnActive]}
              onPress={() => { setMethod('sms'); setStep(STEPS.CONTACT); }}>
              <Text style={s.methodText}>📱  SMS / TEXT</Text>
            </TouchableOpacity>
          </>
        )}

        {step === STEPS.CONTACT && (
          <>
            <Text style={s.label}>{method === 'email' ? 'Email address' : 'Phone number'}</Text>
            <TextInput
              style={s.input}
              placeholder={method === 'email' ? 'pioneer@domain.com' : '+1 000 000 0000'}
              placeholderTextColor={colors.muted}
              value={contact}
              onChangeText={setContact}
              keyboardType={method === 'email' ? 'email-address' : 'phone-pad'}
              autoCapitalize="none"
              autoFocus
            />
            {error ? <Text style={s.error}>{error}</Text> : null}
            <TouchableOpacity style={s.btn} onPress={handleSend} disabled={loading}>
              {loading ? <ActivityIndicator color={colors.black} /> : <Text style={s.btnText}>SEND CODE</Text>}
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setStep(STEPS.METHOD)}>
              <Text style={s.back}>← Back</Text>
            </TouchableOpacity>
          </>
        )}

        {step === STEPS.OTP && (
          <>
            <Text style={s.label}>Enter the 6-digit code sent to</Text>
            <Text style={s.contactDisplay}>{contact}</Text>
            <TextInput
              style={[s.input, s.otpInput]}
              placeholder="000000"
              placeholderTextColor={colors.muted}
              value={otp}
              onChangeText={setOtp}
              keyboardType="number-pad"
              maxLength={6}
              autoFocus
            />
            {error ? <Text style={s.error}>{error}</Text> : null}
            <TouchableOpacity style={s.btn} onPress={handleVerify} disabled={loading}>
              {loading ? <ActivityIndicator color={colors.black} /> : <Text style={s.btnText}>ENTER THE RIDGE</Text>}
            </TouchableOpacity>
            <TouchableOpacity onPress={() => { setOtp(''); setStep(STEPS.CONTACT); }}>
              <Text style={s.back}>← Resend code</Text>
            </TouchableOpacity>
          </>
        )}

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.black },
  inner: { flexGrow: 1, justifyContent: 'center', padding: spacing.xl },
  wordmark: { color: colors.ridge, fontSize: 32, ...fonts.heading, textAlign: 'center', marginBottom: 4 },
  sub: { color: colors.muted, fontSize: 11, ...fonts.heading, textAlign: 'center', marginBottom: spacing.xl * 1.5 },
  label: { color: colors.white, fontSize: 14, ...fonts.sub, marginBottom: spacing.md },
  contactDisplay: { color: colors.ridge, fontSize: 15, marginBottom: spacing.md, textAlign: 'center' },
  input: {
    backgroundColor: colors.surface, color: colors.white, borderWidth: 1,
    borderColor: colors.border, borderRadius: 4, padding: spacing.md,
    fontSize: 16, marginBottom: spacing.md,
  },
  otpInput: { textAlign: 'center', fontSize: 28, letterSpacing: 12, ...fonts.mono },
  methodBtn: {
    borderWidth: 1, borderColor: colors.border, borderRadius: 4,
    padding: spacing.md, marginBottom: spacing.sm, alignItems: 'center',
  },
  methodBtnActive: { borderColor: colors.ridge },
  methodText: { color: colors.white, ...fonts.sub, letterSpacing: 2 },
  btn: {
    backgroundColor: colors.ridge, borderRadius: 4, padding: spacing.md + 2,
    alignItems: 'center', marginTop: spacing.sm,
  },
  btnText: { color: colors.black, fontWeight: '800', letterSpacing: 2, fontSize: 14 },
  error: { color: colors.error, fontSize: 13, marginBottom: spacing.sm },
  back: { color: colors.muted, textAlign: 'center', marginTop: spacing.md, fontSize: 13 },
});
