import { useState } from 'react';
import { Colors } from '@/src/theme/colors';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, TextInput } from 'react-native';
import { router } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProperties, deleteProperty } from '@/src/api/properties';
import { BottomNav } from './dashboard';

const GREEN = Colors.primary;

interface Property {
    id: number;
    name: string;
    city?: string;
    state?: string;
    status: string;
}

export default function PropertiesScreen() {
    const [search, setSearch] = useState('');
    const qc = useQueryClient();

    const { data, isLoading } = useQuery({
        queryKey: ['properties'],
        queryFn: getProperties,
    });

    const deleteMutation = useMutation({
        mutationFn: deleteProperty,
        onSuccess: () => qc.invalidateQueries({ queryKey: ['properties'] }),
    });

    const properties: Property[] = data?.data ?? [];
    const filtered = properties.filter((p) =>
        p.name.toLowerCase().includes(search.toLowerCase())
    );

    const confirmDelete = (id: number, name: string) => {
        Alert.alert('Delete Property', `Are you sure you want to delete "${name}"?`, [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Delete', style: 'destructive', onPress: () => deleteMutation.mutate(id) },
        ]);
    };

    return (
        <View style={styles.flex}>
            {/* Header */}
            <View style={styles.header}>
                <Text style={styles.pageTitle}>My Properties</Text>
                <Text style={styles.pageSubtitle}>Manage your sports venues</Text>
                <TouchableOpacity style={styles.addBtn} onPress={() => router.push('/(owner)/properties/new')}>
                    <MaterialIcons name="add" size={24} color="#fff" />
                </TouchableOpacity>
            </View>

            {/* Search */}
            <View style={styles.searchContainer}>
                <MaterialIcons name="search" size={18} color="#94a3b8" style={styles.searchIcon} />
                <TextInput
                    style={styles.searchInput}
                    placeholder="Search properties, city, or state..."
                    placeholderTextColor="#94a3b8"
                    value={search}
                    onChangeText={setSearch}
                />
            </View>

            <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
                {isLoading ? (
                    <ActivityIndicator color={GREEN} style={{ marginTop: 40 }} />
                ) : filtered.length === 0 ? (
                    <View style={styles.emptyState}>
                        <MaterialIcons name="domain-disabled" size={48} color="#e2e8f0" />
                        <Text style={styles.emptyText}>No properties yet</Text>
                        <TouchableOpacity style={styles.emptyBtn} onPress={() => router.push('/(owner)/properties/new')}>
                            <Text style={styles.emptyBtnText}>Add Your First Property</Text>
                        </TouchableOpacity>
                    </View>
                ) : (
                    filtered.map((property) => (
                        <PropertyCard
                            key={property.id}
                            property={property}
                            onDelete={() => confirmDelete(property.id, property.name)}
                            onEdit={() => router.push(`/(owner)/properties/${property.id}/edit` as any)}
                            onView={() => router.push(`/(owner)/properties/${property.id}` as any)}
                        />
                    ))
                )}
            </ScrollView>

            <BottomNav active="properties" />
        </View>
    );
}

function PropertyCard({ property, onDelete, onEdit, onView }: {
    property: Property;
    onDelete: () => void;
    onEdit: () => void;
    onView: () => void;
}) {
    const isActive = property.status?.toLowerCase() === 'active';
    return (
        <View style={styles.card}>
            <View style={styles.cardHeader}>
                <View style={styles.cardIconWrap}>
                    <MaterialIcons name="sports-tennis" size={20} color={GREEN} />
                </View>
                <View style={styles.cardInfo}>
                    <Text style={styles.cardName}>{property.name}</Text>
                    {(property.city || property.state) ? (
                        <View style={styles.locationRow}>
                            <MaterialIcons name="location-on" size={12} color="#94a3b8" />
                            <Text style={styles.locationText}>
                                {[property.city, property.state].filter(Boolean).join(', ')}
                            </Text>
                        </View>
                    ) : null}
                </View>
                <View style={[styles.statusBadge, isActive ? styles.badgeActive : styles.badgeDraft]}>
                    <Text style={[styles.statusText, isActive ? styles.statusTextActive : styles.statusTextDraft]}>
                        {isActive ? 'ACTIVE' : (property.status?.toUpperCase() ?? 'DRAFT')}
                    </Text>
                </View>
            </View>

            <View style={styles.cardActions}>
                <TouchableOpacity style={styles.actionView} onPress={onView}>
                    <MaterialIcons name="visibility" size={16} color="#fff" />
                    <Text style={styles.actionViewText}>VIEW</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.actionEdit} onPress={onEdit}>
                    <MaterialIcons name="edit" size={16} color="#64748b" />
                    <Text style={styles.actionEditText}>EDIT</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.actionDelete} onPress={onDelete}>
                    <MaterialIcons name="delete-outline" size={16} color="#ef4444" />
                    <Text style={styles.actionDeleteText}>DELETE</Text>
                </TouchableOpacity>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    flex: { flex: 1, backgroundColor: '#f9fafb' },
    scroll: { flex: 1 },
    scrollContent: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 16 },
    header: {
        paddingHorizontal: 20,
        paddingTop: 52,
        paddingBottom: 16,
        backgroundColor: '#fff',
        borderBottomWidth: 1,
        borderBottomColor: '#f1f5f9',
    },
    pageTitle: { fontSize: 26, fontWeight: '800', color: '#0f172a', letterSpacing: -0.4 },
    pageSubtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },
    addBtn: {
        position: 'absolute',
        right: 20,
        bottom: 16,
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: GREEN,
        alignItems: 'center',
        justifyContent: 'center',
    },
    searchContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#fff',
        marginHorizontal: 16,
        marginTop: 14,
        marginBottom: 4,
        borderRadius: 12,
        paddingHorizontal: 12,
        height: 44,
        borderWidth: 1,
        borderColor: '#f1f5f9',
    },
    searchIcon: { marginRight: 8 },
    searchInput: { flex: 1, fontSize: 14, color: '#0f172a' },
    card: {
        backgroundColor: '#fff',
        borderRadius: 16,
        marginTop: 12,
        borderWidth: 1,
        borderColor: '#f1f5f9',
        overflow: 'hidden',
    },
    cardHeader: { flexDirection: 'row', alignItems: 'center', padding: 16, gap: 12 },
    cardIconWrap: {
        width: 42, height: 42, borderRadius: 12,
        backgroundColor: '#ecfdf5', alignItems: 'center', justifyContent: 'center',
    },
    cardInfo: { flex: 1 },
    cardName: { fontSize: 15, fontWeight: '700', color: '#0f172a' },
    locationRow: { flexDirection: 'row', alignItems: 'center', gap: 2, marginTop: 3 },
    locationText: { fontSize: 12, color: '#94a3b8' },
    statusBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
    badgeActive: { backgroundColor: '#dcfce7' },
    badgeDraft: { backgroundColor: '#f1f5f9' },
    statusText: { fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
    statusTextActive: { color: '#16a34a' },
    statusTextDraft: { color: '#64748b' },
    cardActions: {
        flexDirection: 'row',
        borderTopWidth: 1,
        borderTopColor: '#f1f5f9',
    },
    actionView: {
        flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
        gap: 6, paddingVertical: 12, backgroundColor: GREEN,
    },
    actionViewText: { fontSize: 11, fontWeight: '800', color: '#fff', letterSpacing: 0.5 },
    actionEdit: {
        flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
        gap: 6, paddingVertical: 12, borderLeftWidth: 1, borderLeftColor: '#f1f5f9',
    },
    actionEditText: { fontSize: 11, fontWeight: '800', color: '#64748b', letterSpacing: 0.5 },
    actionDelete: {
        flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
        gap: 6, paddingVertical: 12, borderLeftWidth: 1, borderLeftColor: '#f1f5f9',
    },
    actionDeleteText: { fontSize: 11, fontWeight: '800', color: '#ef4444', letterSpacing: 0.5 },
    emptyState: { alignItems: 'center', marginTop: 60, gap: 12 },
    emptyText: { fontSize: 16, color: '#94a3b8', fontWeight: '600' },
    emptyBtn: { backgroundColor: GREEN, borderRadius: 12, paddingHorizontal: 24, paddingVertical: 12, marginTop: 4 },
    emptyBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },
});
