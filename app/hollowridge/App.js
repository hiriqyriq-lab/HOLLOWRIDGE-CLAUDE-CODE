import React, { useEffect, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { getUser } from './src/services/auth';
import AuthScreen from './src/screens/AuthScreen';
import AppNavigator from './src/navigation/AppNavigator';
import { colors } from './src/theme';

export default function App() {
  const [user, setUser] = useState(undefined); // undefined = loading

  useEffect(() => {
    getUser().then(setUser);
  }, []);

  if (user === undefined) {
    return (
      <View style={s.loading}>
        <ActivityIndicator color={colors.ridge} size="large" />
      </View>
    );
  }

  return (
    <>
      <StatusBar style="light" />
      {user
        ? <AppNavigator user={user} onSignOut={() => setUser(null)} />
        : <AuthScreen onAuthed={setUser} />
      }
    </>
  );
}

const s = StyleSheet.create({
  loading: { flex: 1, backgroundColor: colors.black, justifyContent: 'center', alignItems: 'center' },
});
