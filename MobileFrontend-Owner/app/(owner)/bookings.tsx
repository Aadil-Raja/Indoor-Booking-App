import { useState } from 'react';
import { Colors } from '@/src/theme/colors';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/src/api/client';
import { BottomNav } from './dashboard';

const GREEN = Colors.primary;

const DAYS_SHORT = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
const FULL_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const today = new Date();

function getWeekDays() {
    const days = [];
    for (let i = -2; i <= 4; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() + i);
        days.push(d);
    }
    return days;
}

interface Booking {
    id: number;
    court_name?: string;
    customer_name?: string;
    start_time: string;
    end_time: string;
    booking_date: string;
    status: string;
    total_price?: number;
}

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
    confirmed: { bg: '#dcfce7', text: '#16a34a' },
    pending: { bg: '#fef9c3', text: '#a16207' },
    cancelled: { bg: '#fee2e2', text: '#dc2626' },
};

export default function BookingsScreen() {
    const [selectedDate, setSelectedDate] = useState(today);
    const weekDays = getWeekDays();

    const dateStr = selectedDate.toISOString().slice(0, 10);
    const { data, isLoading } = useQuery({
        queryKey: ['bookings', 'owner'],
        queryFn: async () => {
            const res = await apiClient.get('/bookings/owner');
            return res.data;
        },
    });

    // Filter bookings by selected date on client side
    const allBookings: Booking[] = data?.data ?? [];
    const bookings = allBookings.filter((b) => b.booking_date?.slice(0, 10) === dateStr);

    const dayName = selectedDate.toLocaleDateString('en-US', { weekday: 'long' });
    const dayFull = `${dayName}, ${selectedDate.getDate()} ${selectedDate.toLocaleDateString('en-US', { month: 'long' })}`;

    return (
        <View style={styles.flex}>
            <View style={styles.header}>
                <Text style={styles.pageTitle}>Bookings</Text>
                <View style={styles.headerIcons}>
                    <TouchableOpacity><MaterialIcons name="filter-list" size={22} color="#64748b" /></TouchableOpacity>
                    <TouchableOpacity><MaterialIcons name="search" size={22} color="#64748b" /></TouchableOpacity>
                </View>
            </View>

            {/* Week Selector */}
            <View style={styles.weekRow}>
                {weekDays.map((d, i) => {
                    const isSelected = d.toDateString() === selectedDate.toDateString();
                    const isToday = d.toDateString() === today.toDateString();
                    return (
                        <TouchableOpacity
                            key={i}
                            style={styles.dayCol}
                            onPress={() => setSelectedDate(d)}
                        >
                            <Text style={[styles.dayLabel, isSelected && styles.dayLabelActive]}>
                                {DAYS_SHORT[d.getDay() === 0 ? 6 : d.getDay() - 1]}
                            </Text>
                            <View style={[styles.dayCircle, isSelected && styles.dayCircleActive]}>
                                <Text style={[styles.dayNum, isSelected && styles.dayNumActive]}>{d.getDate()}</Text>
                            </View>
                            {isToday && <View style={styles.todayDot} />}
                        </TouchableOpacity>
                    );
                })}
            </View>

            <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
                {/* Day Header */}
                <View style={styles.dayHeader}>
                    <Text style={styles.dayTitle}>{dayFull}</Text>
                    <TouchableOpacity>
                        <Text style={styles.viewAll}>View All</Text>
                    </TouchableOpacity>
                </View>
                {bookings.length > 0 && (
                    <Text style={styles.bookingCount}>{bookings.length} booking{bookings.length !== 1 ? 's' : ''} scheduled for today</Text>
                )}

                {isLoading ? (
                    <ActivityIndicator color={GREEN} style={{ marginTop: 40 }} />
                ) : bookings.length === 0 ? (
                    <View style={styles.emptyState}>
                        <MaterialIcons name="event-busy" size={48} color="#e2e8f0" />
                        <Text style={styles.emptyText}>No bookings for this day</Text>
                    </View>
                ) : (
                    bookings.map((b) => <BookingCard key={b.id} booking={b} />)
                )}
            </ScrollView>

            <TouchableOpacity style={styles.fab}>
                <MaterialIcons name="add" size={26} color="#fff" />
            </TouchableOpacity>

            <BottomNav active="bookings" />
        </View>
    );
}

function BookingCard({ booking }: { booking: Booking }) {
    const statusKey = booking.status?.toLowerCase() ?? 'pending';
    const colors = STATUS_COLORS[statusKey] ?? { bg: '#f1f5f9', text: '#64748b' };
    const start = booking.start_time?.slice(11, 16) ?? '';
    const end = booking.end_time?.slice(11, 16) ?? '';
    return (
        <View style={styles.bookingCard}>
            <View style={styles.bookingLeft}>
                <View style={styles.bookingIcon}>
                    <MaterialIcons name="sports-tennis" size={18} color={GREEN} />
                </View>
                <View>
                    <Text style={styles.bookingCourt}>{booking.court_name ?? 'Court'}</Text>
                    <Text style={styles.bookingUser}>{booking.customer_name ?? ''}</Text>
                    <View style={styles.bookingTime}>
                        <MaterialIcons name="schedule" size={12} color="#94a3b8" />
                        <Text style={styles.bookingTimeText}>{start}-{end}</Text>
                    </View>
                </View>
            </View>
            <View style={styles.bookingRight}>
                <View style={[styles.statusBadge, { backgroundColor: colors.bg }]}>
                    <Text style={[styles.statusText, { color: colors.text }]}>{booking.status?.toUpperCase()}</Text>
                </View>
                <MaterialIcons name="more-horiz" size={20} color="#94a3b8" />
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    flex: { flex: 1, backgroundColor: '#f9fafb' },
    scroll: { flex: 1 },
    scrollContent: { paddingHorizontal: 16, paddingBottom: 16 },
    header: {
        flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end',
        paddingHorizontal: 20, paddingTop: 52, paddingBottom: 16,
        backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#f1f5f9',
    },
    pageTitle: { fontSize: 26, fontWeight: '800', color: '#0f172a', letterSpacing: -0.4 },
    headerIcons: { flexDirection: 'row', gap: 14, paddingBottom: 2 },
    weekRow: {
        flexDirection: 'row', backgroundColor: '#fff',
        paddingHorizontal: 12, paddingBottom: 14, paddingTop: 10,
        borderBottomWidth: 1, borderBottomColor: '#f1f5f9',
    },
    dayCol: { flex: 1, alignItems: 'center', gap: 6 },
    dayLabel: { fontSize: 10, fontWeight: '700', color: '#94a3b8', letterSpacing: 0.4 },
    dayLabelActive: { color: GREEN },
    dayCircle: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
    dayCircleActive: { backgroundColor: GREEN },
    dayNum: { fontSize: 14, fontWeight: '700', color: '#0f172a' },
    dayNumActive: { color: '#fff' },
    todayDot: { width: 4, height: 4, borderRadius: 2, backgroundColor: GREEN },
    dayHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, marginBottom: 4 },
    dayTitle: { fontSize: 16, fontWeight: '800', color: '#0f172a' },
    viewAll: { fontSize: 13, fontWeight: '700', color: GREEN },
    bookingCount: { fontSize: 12, color: '#94a3b8', marginBottom: 12 },
    bookingCard: {
        flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
        backgroundColor: '#fff', borderRadius: 14, padding: 14, marginBottom: 10,
        borderWidth: 1, borderColor: '#f1f5f9',
    },
    bookingLeft: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
    bookingIcon: {
        width: 38, height: 38, borderRadius: 10,
        backgroundColor: '#ecfdf5', alignItems: 'center', justifyContent: 'center', marginTop: 2,
    },
    bookingCourt: { fontSize: 14, fontWeight: '700', color: '#0f172a' },
    bookingUser: { fontSize: 12, color: '#64748b', marginTop: 1 },
    bookingTime: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4 },
    bookingTimeText: { fontSize: 12, color: '#94a3b8' },
    bookingRight: { alignItems: 'flex-end', gap: 8 },
    statusBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
    statusText: { fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
    fab: {
        position: 'absolute', bottom: 96, left: 20,
        width: 52, height: 52, borderRadius: 26,
        backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center',
        elevation: 4,
    },
    emptyState: { alignItems: 'center', marginTop: 60, gap: 10 },
    emptyText: { fontSize: 15, fontWeight: '600', color: '#94a3b8' },
});
