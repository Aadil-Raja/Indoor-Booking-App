import { useState } from 'react';
import { router } from 'expo-router';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    Alert,
    ScrollView,
    ActivityIndicator,
    StatusBar,
    StyleSheet,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { Colors } from '@/src/theme/colors';
import { apiClient } from '@/src/api/client';
import { useAuthStore } from '@/src/store/auth';

export default function SignUpScreen() {
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const { setAuth } = useAuthStore();

    const handleSignUp = async () => {
        if (!firstName || !email || !password) {
            Alert.alert('Error', 'Please fill in First Name, Email and Password.');
            return;
        }
        try {
            setLoading(true);
            const name = `${firstName} ${lastName}`.trim();
            const response = await apiClient.post('/auth/signup', {
                name,
                email,
                password,
                role: 'owner',
            });
            const data = response.data;
            if (data.success) {
                // Signup requires email verification — navigate to OTP screen
                router.replace({ pathname: '/(auth)/verify', params: { email } } as any);
            } else {
                Alert.alert('Sign Up Failed', data.message || 'Could not create account');
            }
        } catch (error: any) {
            const msg = error.response?.data?.message || error.message || 'Sign up failed';
            Alert.alert('Error', msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <View style={styles.flex}>
            <StatusBar barStyle="light-content" backgroundColor={Colors.secondary} />
            <ScrollView
                showsVerticalScrollIndicator={false}
                bounces={false}
                keyboardShouldPersistTaps="handled"
            >
                {/* ── Dark green hero section ── */}
                <View style={styles.hero}>
                    {/* Decorative circles */}
                    <View style={styles.circle1} />
                    <View style={styles.circle2} />
                    <View style={styles.circle3} />

                    <View style={styles.heroContent}>
                        {/* Logo */}
                        <View style={styles.logoRow}>
                            <View style={styles.logoIcon}>
                                <MaterialIcons name="sports-tennis" size={20} color={Colors.white} />
                            </View>
                            <Text style={styles.logoText}>
                                Court<Text style={styles.logoTextGreen}>Hub</Text>
                            </Text>
                        </View>

                        {/* JOIN TODAY badge */}
                        <View style={styles.badge}>
                            <View style={styles.badgeDot} />
                            <Text style={styles.badgeText}>JOIN TODAY</Text>
                        </View>

                        {/* Hero headline */}
                        <Text style={styles.heroTitle}>
                            YOUR GAME,{'\n'}
                            <Text style={styles.heroTitleGreen}>YOUR COURT.</Text>
                        </Text>

                        <Text style={styles.heroSubtitle}>
                            List your sports facilities and reach thousands of players looking for their next game.
                        </Text>
                    </View>
                </View>

                {/* ── White form card ── */}
                <View style={styles.card}>
                    {/* Step indicator dots */}
                    <View style={styles.stepDots}>
                        <View style={[styles.dot, styles.dotActive]} />
                        <View style={styles.dot} />
                    </View>

                    <Text style={styles.cardTitle}>CREATE ACCOUNT</Text>
                    <Text style={styles.cardSubtitle}>Join CourtHub and start managing your venues</Text>

                    {/* First + Last Name */}
                    <View style={styles.nameRow}>
                        <View style={styles.halfField}>
                            <Text style={styles.label}>FIRST NAME</Text>
                            <TextInput
                                style={styles.input}
                                placeholder="John"
                                placeholderTextColor={Colors.gray400}
                                value={firstName}
                                onChangeText={setFirstName}
                                autoCapitalize="words"
                            />
                        </View>
                        <View style={styles.halfField}>
                            <Text style={styles.label}>LAST NAME</Text>
                            <TextInput
                                style={styles.input}
                                placeholder="Doe"
                                placeholderTextColor={Colors.gray400}
                                value={lastName}
                                onChangeText={setLastName}
                                autoCapitalize="words"
                            />
                        </View>
                    </View>

                    {/* Email */}
                    <View style={styles.fieldGroup}>
                        <Text style={styles.label}>EMAIL</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="aadil2raja@gmail.com"
                            placeholderTextColor={Colors.gray400}
                            value={email}
                            onChangeText={setEmail}
                            keyboardType="email-address"
                            autoCapitalize="none"
                            autoCorrect={false}
                        />
                    </View>

                    {/* Phone */}
                    <View style={styles.fieldGroup}>
                        <Text style={styles.label}>PHONE (OPTIONAL)</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="+1 234 567 8900"
                            placeholderTextColor={Colors.gray400}
                            value={phone}
                            onChangeText={setPhone}
                            keyboardType="phone-pad"
                        />
                    </View>

                    {/* Password */}
                    <View style={styles.fieldGroup}>
                        <Text style={styles.label}>PASSWORD</Text>
                        <View style={styles.passwordContainer}>
                            <TextInput
                                style={styles.passwordInput}
                                placeholder="••••••••"
                                placeholderTextColor={Colors.gray400}
                                value={password}
                                onChangeText={setPassword}
                                secureTextEntry={!showPassword}
                                autoCapitalize="none"
                            />
                            <TouchableOpacity
                                onPress={() => setShowPassword(!showPassword)}
                                style={styles.eyeBtn}
                                hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                            >
                                <MaterialIcons
                                    name={showPassword ? 'visibility' : 'visibility-off'}
                                    size={20}
                                    color={Colors.gray400}
                                />
                            </TouchableOpacity>
                        </View>
                    </View>

                    {/* Continue Button */}
                    <TouchableOpacity
                        style={[styles.continueBtn, loading && styles.continueBtnDisabled]}
                        onPress={handleSignUp}
                        disabled={loading}
                        activeOpacity={0.88}
                    >
                        {loading ? (
                            <ActivityIndicator color={Colors.white} />
                        ) : (
                            <>
                                <Text style={styles.continueBtnText}>Continue</Text>
                                <MaterialIcons name="arrow-forward" size={20} color={Colors.white} />
                            </>
                        )}
                    </TouchableOpacity>

                    {/* Sign in link */}
                    <View style={styles.footer}>
                        <Text style={styles.footerText}>Already have an account? </Text>
                        <TouchableOpacity onPress={() => router.replace('/(auth)/login')}>
                            <Text style={styles.signInLink}>Sign in</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    flex: { flex: 1, backgroundColor: Colors.secondary },

    // Hero
    hero: {
        backgroundColor: Colors.secondary,
        paddingTop: 70,
        paddingBottom: 85,
        paddingHorizontal: 24,
        overflow: 'hidden',
    },
    heroContent: {
        alignItems: 'center',
    },
    circle1: {
        position: 'absolute', top: 40, left: 40,
        width: 80, height: 80, borderRadius: 40, backgroundColor: 'rgba(255,255,255,0.05)',
    },
    circle2: {
        position: 'absolute', bottom: 80, right: 40,
        width: 128, height: 128, borderRadius: 64, backgroundColor: 'rgba(255,255,255,0.05)',
    },
    circle3: {
        position: 'absolute', top: '50%', left: '25%',
        width: 48, height: 48, borderRadius: 24, backgroundColor: 'rgba(255,255,255,0.05)',
    },
    logoRow: {
        flexDirection: 'row', alignItems: 'center',
        gap: 8, marginBottom: 20,
    },
    logoIcon: {
        width: 38, height: 38, borderRadius: 10,
        backgroundColor: Colors.primary,
        alignItems: 'center', justifyContent: 'center',
    },
    logoText: { fontSize: 22, fontWeight: '800', color: Colors.white },
    logoTextGreen: { color: Colors.primary },
    badge: {
        flexDirection: 'row', alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.12)',
        paddingHorizontal: 14, paddingVertical: 5,
        borderRadius: 20, borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)',
        marginBottom: 20,
    },
    badgeDot: {
        width: 6, height: 6, borderRadius: 3,
        backgroundColor: Colors.primary, marginRight: 6,
    },
    badgeText: { fontSize: 10, fontWeight: '800', color: Colors.white, letterSpacing: 1.5 },
    heroTitle: {
        fontSize: 38, fontWeight: '900', color: Colors.white,
        textAlign: 'center', letterSpacing: -0.5, lineHeight: 44,
        fontStyle: 'italic', textTransform: 'uppercase', marginBottom: 14,
    },
    heroTitleGreen: { color: Colors.primary },
    heroSubtitle: {
        fontSize: 13, color: 'rgba(255,255,255,0.65)',
        textAlign: 'center', lineHeight: 20, maxWidth: 280,
    },

    // Card
    card: {
        backgroundColor: Colors.white,
        borderTopLeftRadius: 40,
        borderTopRightRadius: 40,
        marginTop: -40,
        paddingHorizontal: 28,
        paddingTop: 36,
        paddingBottom: 60,
        minHeight: 550, // Ensures layout isn't empty at bottom
        // Shadow where card meets hero
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -10 },
        shadowOpacity: 0.08,
        shadowRadius: 15,
        elevation: 10,
    },
    stepDots: {
        flexDirection: 'row', justifyContent: 'center',
        gap: 6, marginBottom: 24,
    },
    dot: { width: 28, height: 5, borderRadius: 3, backgroundColor: Colors.gray200 },
    dotActive: { backgroundColor: Colors.primary },
    cardTitle: {
        fontSize: 28, fontWeight: '900', color: Colors.gray900,
        textAlign: 'center', letterSpacing: -0.5,
        fontStyle: 'italic', textTransform: 'uppercase',
    },
    cardSubtitle: { fontSize: 13, color: Colors.gray500, textAlign: 'center', marginTop: 4, marginBottom: 28 },

    // Form fields
    nameRow: { flexDirection: 'row', gap: 12, marginBottom: 16 },
    halfField: { flex: 1, gap: 5 },
    fieldGroup: { gap: 5, marginBottom: 16 },
    label: { fontSize: 10, fontWeight: '800', color: Colors.gray400, letterSpacing: 0.8 },
    input: {
        height: 50, backgroundColor: Colors.gray100,
        borderRadius: 14, paddingHorizontal: 16,
        fontSize: 14, color: Colors.gray900,
    },
    passwordContainer: {
        flexDirection: 'row', alignItems: 'center',
        backgroundColor: Colors.gray100, borderRadius: 14, height: 50,
    },
    passwordInput: { flex: 1, paddingHorizontal: 16, fontSize: 14, color: Colors.gray900 },
    eyeBtn: { padding: 12 },

    // Continue button
    continueBtn: {
        height: 54, borderRadius: 16, backgroundColor: Colors.primary,
        flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
        gap: 8, marginTop: 12,
        // Premium Shadow
        shadowColor: Colors.primary,
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.35,
        shadowRadius: 12,
        elevation: 8,
    },
    continueBtnDisabled: { opacity: 0.6 },
    continueBtnText: { fontSize: 16, fontWeight: '700', color: Colors.white },

    // Footer
    footer: {
        flexDirection: 'row', justifyContent: 'center',
        alignItems: 'center', marginTop: 24,
    },
    footerText: { fontSize: 14, color: Colors.gray500 },
    signInLink: { fontSize: 14, fontWeight: '800', color: Colors.primary },
});
