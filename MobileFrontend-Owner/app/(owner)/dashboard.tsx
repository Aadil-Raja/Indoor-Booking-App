import { useEffect } from 'react';
import { Colors } from '@/src/theme/colors';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { router } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/src/store/auth';
import { getDashboard } from '@/src/api/owner';

const GREEN = Colors.primary;

interface DashboardData {
    total_properties: number;
    total_courts: number;
    total_bookings: number;
    total_revenue: number;
}

function StatCard({ icon, iconBg, iconColor, value, label }: {
    icon: string; iconBg: string; iconColor: string; value: string; label: string;
}) {
    return (
        <View style={styles.statCard}>
            <View style={[styles.statIconBox, { backgroundColor: iconBg }]}>
                <MaterialIcons name={icon as any} size={22} color={iconColor} />
            </View>
            <Text style={styles.statValue}>{value}</Text>
            <Text style={styles.statLabel}>{label}</Text>
        </View>
    );
}

export default function DashboardScreen() {
    const { user, logout } = useAuthStore();

    const { data, isLoading } = useQuery({
        queryKey: ['dashboard'],
        queryFn: getDashboard,
    });

    const stats: DashboardData = data?.data ?? {
        total_properties: 0,
        total_courts: 0,
        total_bookings: 0,
        total_revenue: 0,
    };

    return (
        <View style={styles.flex}>
            {/* Header */}
            <View style={styles.header}>
                <View style={styles.headerLeft}>
                    <View style={styles.headerLogo}>
                        <MaterialIcons name="sports-tennis" size={16} color="#fff" />
                    </View>
                    <Text style={styles.headerTitle}>CourtHub</Text>
                </View>
                <View style={styles.headerRight}>
                    <TouchableOpacity style={styles.notifBtn}>
                        <MaterialIcons name="notifications" size={22} color="#64748b" />
                    </TouchableOpacity>
                    <View style={styles.avatarCircle}>
                        <Text style={styles.avatarText}>{user?.name?.[0]?.toUpperCase() ?? 'O'}</Text>
                    </View>
                </View>
            </View>

            <ScrollView showsVerticalScrollIndicator={false} style={styles.scroll}>
                {/* Title */}
                <View style={styles.titleSection}>
                    <Text style={styles.pageTitle}>Dashboard</Text>
                    <Text style={styles.pageSubtitle}>Welcome back! Here's an overview of your business.</Text>
                </View>

                {/* Stats Grid */}
                {isLoading ? (
                    <ActivityIndicator color={GREEN} style={{ marginTop: 24 }} />
                ) : (
                    <View style={styles.statsGrid}>
                        <StatCard icon="domain" iconBg="#eff6ff" iconColor="#3b82f6" value={String(stats.total_properties)} label="PROPERTIES" />
                        <StatCard icon="sports-tennis" iconBg="#ecfdf5" iconColor={GREEN} value={String(stats.total_courts)} label="COURTS" />
                        <StatCard icon="event-available" iconBg="#fffbeb" iconColor="#f59e0b" value={String(stats.total_bookings)} label="BOOKINGS" />
                        <StatCard icon="payments" iconBg="#eef2ff" iconColor="#6366f1" value={`₹${stats.total_revenue}`} label="REVENUE" />
                    </View>
                )}

                {/* Get Started */}
                <View style={styles.getStartedSection}>
                    <View style={styles.getStartedHeader}>
                        <Text style={styles.getStartedTitle}>Get Started</Text>
                        <View style={styles.completedBadge}>
                            <Text style={styles.completedText}>0/3 Completed</Text>
                        </View>
                    </View>
                    <Text style={styles.getStartedSubtitle}>
                        Follow these steps to set up your indoor booking business
                    </Text>

                    <View style={styles.stepsList}>
                        <StepCard
                            num={1}
                            active
                            title="Complete Your Profile"
                            desc="Add your business information to build trust."
                            cta="Go to Profile"
                            onPress={() => { }}
                        />
                        <StepCard
                            num={2}
                            active={false}
                            title="Add Your First Property"
                            desc="Create a property to manage your courts."
                            cta="Add Property"
                            onPress={() => router.push('/(owner)/properties')}
                        />
                        <StepCard
                            num={3}
                            active={false}
                            title="Add Courts & Set Pricing"
                            desc="Configure your courts and dynamic pricing rules."
                            cta="Manage Properties"
                            onPress={() => router.push('/(owner)/properties')}
                        />
                    </View>
                </View>
            </ScrollView>

            {/* Bottom Nav */}
            <BottomNav active="dashboard" />
        </View>
    );
}

function StepCard({ num, active, title, desc, cta, onPress }: {
    num: number; active: boolean; title: string; desc: string; cta: string; onPress: () => void;
}) {
    return (
        <View style={[styles.stepCard, active && styles.stepCardActive]}>
            <View style={[styles.stepNum, active ? styles.stepNumActive : styles.stepNumInactive]}>
                <Text style={[styles.stepNumText, active ? { color: '#fff' } : { color: '#64748b' }]}>{num}</Text>
            </View>
            <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>{title}</Text>
                <Text style={styles.stepDesc}>{desc}</Text>
                <TouchableOpacity onPress={onPress} style={styles.stepCta}>
                    <Text style={styles.stepCtaText}>{cta}</Text>
                    <MaterialIcons name="arrow-forward" size={14} color={GREEN} />
                </TouchableOpacity>
            </View>
        </View>
    );
}

export function BottomNav({ active }: { active: 'dashboard' | 'properties' | 'courts' | 'bookings' | 'profile' }) {
    const items = [
        { key: 'dashboard', icon: 'dashboard', label: 'Dashboard', route: '/(owner)/dashboard' },
        { key: 'properties', icon: 'domain', label: 'Properties', route: '/(owner)/properties' },
        { key: 'courts', icon: 'sports-tennis', label: 'Courts', route: '/(owner)/courts' },
        { key: 'bookings', icon: 'event-note', label: 'Bookings', route: '/(owner)/bookings' },
        { key: 'profile', icon: 'person', label: 'Profile', route: '/(owner)/profile' },
    ] as const;

    return (
        <View style={nav.container}>
            {items.map((item) => {
                const isActive = item.key === active;
                return (
                    <TouchableOpacity
                        key={item.key}
                        style={nav.item}
                        onPress={() => router.replace(item.route as any)}
                    >
                        <MaterialIcons
                            name={item.icon as any}
                            size={24}
                            color={isActive ? GREEN : '#94a3b8'}
                        />
                        <Text style={[nav.label, isActive && nav.labelActive]}>
                            {item.label.toUpperCase()}
                        </Text>
                    </TouchableOpacity>
                );
            })}
        </View>
    );
}

const styles = StyleSheet.create({
    flex: { flex: 1, backgroundColor: '#f9fafb' },
    scroll: { flex: 1 },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingTop: 52,
        paddingBottom: 14,
        backgroundColor: '#fff',
        borderBottomWidth: 1,
        borderBottomColor: '#f1f5f9',
    },
    headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    headerLogo: {
        width: 30, height: 30, borderRadius: 8,
        backgroundColor: GREEN, alignItems: 'center', justifyContent: 'center',
    },
    headerTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
    headerRight: { flexDirection: 'row', alignItems: 'center', gap: 10 },
    notifBtn: {
        width: 38, height: 38, borderRadius: 19,
        backgroundColor: '#f1f5f9', alignItems: 'center', justifyContent: 'center',
    },
    avatarCircle: {
        width: 38, height: 38, borderRadius: 19,
        backgroundColor: `${GREEN}33`, borderWidth: 2, borderColor: GREEN,
        alignItems: 'center', justifyContent: 'center',
    },
    avatarText: { fontSize: 15, fontWeight: '700', color: GREEN },
    titleSection: { paddingHorizontal: 20, paddingTop: 24, paddingBottom: 4 },
    pageTitle: { fontSize: 26, fontWeight: '800', color: '#0f172a', letterSpacing: -0.4 },
    pageSubtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },
    statsGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        paddingHorizontal: 20,
        marginTop: 20,
        gap: 12,
    },
    statCard: {
        width: '47%',
        backgroundColor: '#fff',
        borderRadius: 16,
        padding: 16,
        borderWidth: 1,
        borderColor: '#f1f5f9',
    },
    statIconBox: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center', marginBottom: 10 },
    statValue: { fontSize: 26, fontWeight: '800', color: '#0f172a' },
    statLabel: { fontSize: 10, fontWeight: '700', color: '#94a3b8', letterSpacing: 0.8, marginTop: 2 },
    getStartedSection: { paddingHorizontal: 20, paddingTop: 28, paddingBottom: 16 },
    getStartedHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    getStartedTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
    completedBadge: { backgroundColor: `${GREEN}1a`, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
    completedText: { fontSize: 11, fontWeight: '700', color: GREEN },
    getStartedSubtitle: { fontSize: 13, color: '#64748b', marginTop: 4, marginBottom: 16 },
    stepsList: { gap: 10 },
    stepCard: {
        flexDirection: 'row',
        backgroundColor: '#fff',
        borderRadius: 14,
        padding: 16,
        gap: 14,
        borderWidth: 1,
        borderColor: '#f1f5f9',
        borderLeftWidth: 4,
        borderLeftColor: '#e2e8f0',
        opacity: 0.75,
    },
    stepCardActive: { borderLeftColor: GREEN, opacity: 1 },
    stepNum: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
    stepNumActive: { backgroundColor: GREEN },
    stepNumInactive: { backgroundColor: '#f1f5f9' },
    stepNumText: { fontSize: 15, fontWeight: '800' },
    stepContent: { flex: 1 },
    stepTitle: { fontSize: 14, fontWeight: '700', color: '#0f172a', marginBottom: 3 },
    stepDesc: { fontSize: 13, color: '#64748b', lineHeight: 18 },
    stepCta: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 8 },
    stepCtaText: { fontSize: 13, fontWeight: '700', color: GREEN },
});

const nav = StyleSheet.create({
    container: {
        flexDirection: 'row',
        backgroundColor: '#fff',
        borderTopWidth: 1,
        borderTopColor: '#f1f5f9',
        paddingBottom: 20,
        paddingTop: 10,
        paddingHorizontal: 8,
    },
    item: { flex: 1, alignItems: 'center', gap: 3 },
    label: { fontSize: 9, fontWeight: '700', color: '#94a3b8', letterSpacing: 0.5 },
    labelActive: { color: GREEN },
});
