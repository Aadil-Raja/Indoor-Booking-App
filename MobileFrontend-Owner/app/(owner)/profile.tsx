import { useState } from 'react';
import { Colors } from '@/src/theme/colors';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert, Switch } from 'react-native';
import { router } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/src/store/auth';
import { getOwnerProfile } from '@/src/api/owner';
import { BottomNav } from './dashboard';

const GREEN = Colors.primary;

export default function ProfileScreen() {
    const { user, logout } = useAuthStore();
    const [darkMode, setDarkMode] = useState(false);

    const { data } = useQuery({
        queryKey: ['owner-profile'],
        queryFn: getOwnerProfile,
    });

    const profile = data?.data;

    const handleLogout = () => {
        Alert.alert('Logout', 'Are you sure you want to logout?', [
            { text: 'Cancel', style: 'cancel' },
            {
                text: 'Logout',
                style: 'destructive',
                onPress: async () => {
                    await logout();
                    router.replace('/(auth)/login');
                },
            },
        ]);
    };

    const displayName = profile?.business_name || user?.name || 'Owner';
    const joinYear = new Date().getFullYear();

    return (
        <View style={styles.flex}>
            <View style={styles.header}>
                <Text style={styles.headerTitle}>Profile</Text>
                <TouchableOpacity>
                    <MaterialIcons name="settings" size={24} color="#64748b" />
                </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false} style={styles.scroll}>
                {/* Avatar & Name */}
                <View style={styles.profileSection}>
                    <View style={styles.avatarWrap}>
                        <View style={styles.avatar}>
                            <Text style={styles.avatarText}>{displayName[0]?.toUpperCase()}</Text>
                        </View>
                        <View style={styles.editAvatarBtn}>
                            <MaterialIcons name="camera-alt" size={14} color="#fff" />
                        </View>
                    </View>
                    <Text style={styles.displayName}>{displayName}</Text>
                    <Text style={styles.roleText}>Venue Owner • Member since {joinYear}</Text>
                    <TouchableOpacity style={styles.editProfileBtn}>
                        <Text style={styles.editProfileText}>Edit Profile</Text>
                    </TouchableOpacity>
                </View>

                {/* Menu Items */}
                <View style={styles.menuSection}>
                    <MenuItem
                        icon="business"
                        iconBg="#fef9c3"
                        iconColor="#ca8a04"
                        label="Business Information"
                        onPress={() => { }}
                    />
                    <MenuItem
                        icon="notifications"
                        iconBg="#fef3c7"
                        iconColor="#d97706"
                        label="Notification Settings"
                        onPress={() => { }}
                    />
                    <View style={styles.menuItem}>
                        <View style={[styles.menuIcon, { backgroundColor: '#ede9fe' }]}>
                            <MaterialIcons name="dark-mode" size={20} color="#7c3aed" />
                        </View>
                        <Text style={styles.menuLabel}>Dark Mode</Text>
                        <Switch
                            value={darkMode}
                            onValueChange={setDarkMode}
                            trackColor={{ false: '#e2e8f0', true: GREEN }}
                            thumbColor="#fff"
                        />
                    </View>
                </View>

                <View style={styles.menuSection}>
                    <MenuItem
                        icon="help-outline"
                        iconBg="#f0f9ff"
                        iconColor="#0ea5e9"
                        label="Help & Support"
                        onPress={() => { }}
                    />
                    <TouchableOpacity style={styles.menuItem} onPress={handleLogout}>
                        <View style={[styles.menuIcon, { backgroundColor: '#fee2e2' }]}>
                            <MaterialIcons name="logout" size={20} color="#ef4444" />
                        </View>
                        <Text style={[styles.menuLabel, { color: '#ef4444' }]}>Logout</Text>
                        <MaterialIcons name="chevron-right" size={20} color="#ef4444" />
                    </TouchableOpacity>
                </View>

                <Text style={styles.version}>CourtHub for Owners • Version 2.4.0 (Build 102)</Text>
            </ScrollView>

            <BottomNav active="profile" />
        </View>
    );
}

function MenuItem({ icon, iconBg, iconColor, label, onPress }: {
    icon: string; iconBg: string; iconColor: string; label: string; onPress: () => void;
}) {
    return (
        <TouchableOpacity style={styles.menuItem} onPress={onPress}>
            <View style={[styles.menuIcon, { backgroundColor: iconBg }]}>
                <MaterialIcons name={icon as any} size={20} color={iconColor} />
            </View>
            <Text style={styles.menuLabel}>{label}</Text>
            <MaterialIcons name="chevron-right" size={20} color="#cbd5e1" />
        </TouchableOpacity>
    );
}

const styles = StyleSheet.create({
    flex: { flex: 1, backgroundColor: '#f9fafb' },
    scroll: { flex: 1 },
    header: {
        flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
        paddingHorizontal: 20, paddingTop: 52, paddingBottom: 16,
        backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#f1f5f9',
    },
    headerTitle: { fontSize: 26, fontWeight: '800', color: '#0f172a', letterSpacing: -0.4 },
    profileSection: { alignItems: 'center', paddingVertical: 32, backgroundColor: '#fff', marginBottom: 12 },
    avatarWrap: { position: 'relative', marginBottom: 14 },
    avatar: {
        width: 90, height: 90, borderRadius: 45,
        backgroundColor: `${GREEN}22`, alignItems: 'center', justifyContent: 'center',
        borderWidth: 3, borderColor: GREEN,
    },
    avatarText: { fontSize: 34, fontWeight: '800', color: GREEN },
    editAvatarBtn: {
        position: 'absolute', bottom: 0, right: 0,
        width: 28, height: 28, borderRadius: 14,
        backgroundColor: GREEN, alignItems: 'center', justifyContent: 'center',
        borderWidth: 2, borderColor: '#fff',
    },
    displayName: { fontSize: 22, fontWeight: '800', color: '#0f172a', letterSpacing: -0.3 },
    roleText: { fontSize: 13, color: '#94a3b8', marginTop: 3 },
    editProfileBtn: { marginTop: 12, paddingVertical: 6, paddingHorizontal: 20 },
    editProfileText: { fontSize: 14, fontWeight: '700', color: GREEN },
    menuSection: {
        backgroundColor: '#fff', borderRadius: 16, marginHorizontal: 16,
        marginBottom: 12, overflow: 'hidden',
    },
    menuItem: {
        flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16,
        paddingVertical: 14, gap: 14,
        borderBottomWidth: 1, borderBottomColor: '#f8fafc',
    },
    menuIcon: { width: 38, height: 38, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
    menuLabel: { flex: 1, fontSize: 15, fontWeight: '600', color: '#0f172a' },
    version: { textAlign: 'center', fontSize: 11, color: '#cbd5e1', marginVertical: 20 },
});
