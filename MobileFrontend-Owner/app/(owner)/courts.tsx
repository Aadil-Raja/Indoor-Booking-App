import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { Colors } from '@/src/theme/colors';
import { router } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCourts, deleteCourt } from '@/src/api/courts';
import { BottomNav } from './dashboard';

const GREEN = Colors.primary;

interface Court {
    id: number;
    name: string;
    sport_type?: string;
    is_active?: boolean;
    property_name?: string;
}

export default function CourtsScreen() {
    const qc = useQueryClient();

    const { data, isLoading } = useQuery({
        queryKey: ['courts'],
        queryFn: getCourts,
    });

    const deleteMutation = useMutation({
        mutationFn: deleteCourt,
        onSuccess: () => qc.invalidateQueries({ queryKey: ['courts'] }),
    });

    const courts: Court[] = data?.data ?? [];

    const confirmDelete = (id: number, name: string) => {
        Alert.alert('Delete Court', `Delete "${name}"?`, [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Delete', style: 'destructive', onPress: () => deleteMutation.mutate(id) },
        ]);
    };

    return (
        <View style={styles.flex}>
            <View style={styles.header}>
                <Text style={styles.pageTitle}>Courts</Text>
                <Text style={styles.pageSubtitle}>Manage your individual courts</Text>
                <TouchableOpacity style={styles.addBtn}>
                    <MaterialIcons name="add" size={24} color="#fff" />
                </TouchableOpacity>
            </View>

            <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
                {isLoading ? (
                    <ActivityIndicator color={GREEN} style={{ marginTop: 40 }} />
                ) : courts.length === 0 ? (
                    <View style={styles.emptyState}>
                        <MaterialIcons name="sports-tennis" size={52} color="#e2e8f0" />
                        <Text style={styles.emptyText}>No courts yet</Text>
                        <Text style={styles.emptySubtext}>Add a property first, then add courts</Text>
                    </View>
                ) : (
                    courts.map((court) => (
                        <CourtCard
                            key={court.id}
                            court={court}
                            onPress={() => router.push(`/(owner)/courts/${court.id}` as any)}
                            onDelete={() => confirmDelete(court.id, court.name)}
                        />
                    ))
                )}
            </ScrollView>

            <BottomNav active="courts" />
        </View>
    );
}

function CourtCard({ court, onPress, onDelete }: {
    court: Court; onPress: () => void; onDelete: () => void;
}) {
    const isActive = court.is_active !== false;
    return (
        <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.8}>
            <View style={styles.cardLeft}>
                <View style={styles.cardIcon}>
                    <MaterialIcons name="sports-tennis" size={20} color={GREEN} />
                </View>
                <View>
                    <Text style={styles.cardName}>{court.name}</Text>
                    {court.property_name && (
                        <Text style={styles.cardSub}>{court.property_name}</Text>
                    )}
                    {court.sport_type && (
                        <Text style={styles.cardSport}>{court.sport_type}</Text>
                    )}
                </View>
            </View>
            <View style={styles.cardRight}>
                <View style={[styles.statusBadge, isActive ? styles.badgeActive : styles.badgeDraft]}>
                    <Text style={[styles.statusText, isActive ? styles.statusTextActive : styles.statusTextDraft]}>
                        {isActive ? 'ACTIVE' : 'INACTIVE'}
                    </Text>
                </View>
                <TouchableOpacity onPress={onDelete} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
                    <MaterialIcons name="delete-outline" size={20} color="#ef4444" />
                </TouchableOpacity>
            </View>
        </TouchableOpacity>
    );
}

const styles = StyleSheet.create({
    flex: { flex: 1, backgroundColor: '#f9fafb' },
    scroll: { flex: 1 },
    scrollContent: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 16 },
    header: {
        paddingHorizontal: 20, paddingTop: 52, paddingBottom: 16,
        backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#f1f5f9',
    },
    pageTitle: { fontSize: 26, fontWeight: '800', color: '#0f172a', letterSpacing: -0.4 },
    pageSubtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },
    addBtn: {
        position: 'absolute', right: 20, bottom: 16,
        width: 44, height: 44, borderRadius: 22,
        backgroundColor: GREEN, alignItems: 'center', justifyContent: 'center',
    },
    card: {
        flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
        backgroundColor: '#fff', borderRadius: 14, padding: 16, marginTop: 10,
        borderWidth: 1, borderColor: '#f1f5f9',
    },
    cardLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
    cardIcon: {
        width: 42, height: 42, borderRadius: 12,
        backgroundColor: '#ecfdf5', alignItems: 'center', justifyContent: 'center',
    },
    cardName: { fontSize: 15, fontWeight: '700', color: '#0f172a' },
    cardSub: { fontSize: 12, color: '#64748b', marginTop: 2 },
    cardSport: { fontSize: 11, color: '#94a3b8', marginTop: 1 },
    cardRight: { flexDirection: 'row', alignItems: 'center', gap: 10 },
    statusBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
    badgeActive: { backgroundColor: '#dcfce7' },
    badgeDraft: { backgroundColor: '#f1f5f9' },
    statusText: { fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
    statusTextActive: { color: '#16a34a' },
    statusTextDraft: { color: '#64748b' },
    emptyState: { alignItems: 'center', marginTop: 80, gap: 8 },
    emptyText: { fontSize: 16, fontWeight: '700', color: '#94a3b8' },
    emptySubtext: { fontSize: 13, color: '#94a3b8' },
});
