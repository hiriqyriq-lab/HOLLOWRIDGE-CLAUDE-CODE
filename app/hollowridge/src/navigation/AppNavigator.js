import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { Text } from 'react-native';
import { colors } from '../theme';

import HomeScreen from '../screens/HomeScreen';
import DropScreen from '../screens/DropScreen';
import LoreScreen from '../screens/LoreScreen';
import NotificationsScreen from '../screens/NotificationsScreen';
import ProfileScreen from '../screens/ProfileScreen';

const Tab = createBottomTabNavigator();
const HomeStack = createStackNavigator();

function HomeStackNav() {
  return (
    <HomeStack.Navigator screenOptions={{
      headerStyle: { backgroundColor: colors.black, borderBottomColor: colors.border, borderBottomWidth: 1 },
      headerTintColor: colors.ridge,
      headerTitleStyle: { fontWeight: '800', letterSpacing: 2, textTransform: 'uppercase' },
    }}>
      <HomeStack.Screen name="Home" component={HomeScreen} options={{ title: 'Hollow Ridge' }} />
      <HomeStack.Screen name="Drop" component={DropScreen} options={({ route }) => ({ title: route.params.drop.title })} />
    </HomeStack.Navigator>
  );
}

const TAB_ICONS = { Shop: '◈', Lore: '⬡', Transmissions: '◉', Profile: '◎' };

export default function AppNavigator({ user, onSignOut }) {
  return (
    <NavigationContainer>
      <Tab.Navigator screenOptions={({ route }) => ({
        tabBarIcon: ({ focused }) => (
          <Text style={{ color: focused ? colors.ridge : colors.muted, fontSize: 16 }}>
            {TAB_ICONS[route.name]}
          </Text>
        ),
        tabBarLabel: ({ focused }) => (
          <Text style={{ color: focused ? colors.ridge : colors.muted, fontSize: 9, letterSpacing: 1, fontWeight: '700', textTransform: 'uppercase' }}>
            {route.name}
          </Text>
        ),
        tabBarStyle: { backgroundColor: colors.black, borderTopColor: colors.border, borderTopWidth: 1 },
        headerShown: false,
      })}>
        <Tab.Screen name="Shop" component={HomeStackNav} />
        <Tab.Screen name="Lore" component={LoreScreen} options={{ headerShown: true, headerStyle: { backgroundColor: colors.black, borderBottomColor: colors.border, borderBottomWidth: 1 }, headerTintColor: colors.ridge, headerTitleStyle: { fontWeight: '800', letterSpacing: 2, textTransform: 'uppercase' }, title: 'Lattice Lore' }} />
        <Tab.Screen name="Transmissions" component={NotificationsScreen} />
        <Tab.Screen name="Profile">{() => <ProfileScreen user={user} onSignOut={onSignOut} />}</Tab.Screen>
      </Tab.Navigator>
    </NavigationContainer>
  );
}
