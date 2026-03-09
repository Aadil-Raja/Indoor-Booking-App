import { Stack } from 'expo-router';

export default function OwnerLayout() {
    return (
        <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="dashboard" />
            <Stack.Screen name="properties" />
            <Stack.Screen name="courts" />
            <Stack.Screen name="bookings" />
            <Stack.Screen name="profile" />
        </Stack>
    );
}
