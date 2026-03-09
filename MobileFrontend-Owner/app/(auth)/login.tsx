import { useState } from 'react';
import { router } from 'expo-router';
import { Colors } from '@/src/theme/colors';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    Alert,
    ScrollView,
    ActivityIndicator,
    StatusBar,
    KeyboardAvoidingView,
    Platform,
    StyleSheet,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { useAuthStore } from '@/src/store/auth';
import { loginWithPassword, loginRequestCode } from '@/src/api/auth';

export default function LoginScreen() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const { setAuth } = useAuthStore();

    const handleLogin = async () => {
        if (!email || !password) {
            Alert.alert('Error', 'Please enter both email and password.');
            return;
        }
        try {
            setLoading(true);
            const response = await loginWithPassword(email, password);
            if (response.success && response.data?.access_token) {
                await setAuth(response.data.access_token, { name: response.data.name, email });
                router.replace('/(owner)/dashboard');
            } else {
                Alert.alert('Login Failed', response.message || 'Invalid credentials');
            }
        } catch (error: any) {
            const msg = error.response?.data?.message || error.message || 'Login failed';
            Alert.alert('Error', msg);
        } finally {
            setLoading(false);
        }
    };

    const handleOTPLogin = async () => {
        if (!email) {
            Alert.alert('Error', 'Please enter your email address first.');
            return;
        }
        try {
            setLoading(true);
            const response = await loginRequestCode(email);
            if (response.success) {
                router.push({ pathname: '/(auth)/verify', params: { email, mode: 'login' } } as any);
            } else {
                Alert.alert('Error', response.message || 'Could not send login code');
            }
        } catch (error: any) {
            const msg = error.response?.data?.message || error.message || 'Failed to send code';
            Alert.alert('Error', msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={styles.flex}
        >
            <StatusBar barStyle="dark-content" backgroundColor="#fff" />
            <ScrollView
                contentContainerStyle={styles.container}
                keyboardShouldPersistTaps="handled"
                showsVerticalScrollIndicator={false}
            >
                {/* Logo — centered */}
                <View style={styles.logoContainer}>
                    <View style={styles.logoIcon}>
                        <MaterialIcons name="sports-tennis" size={20} color="#fff" />
                    </View>
                    <Text style={styles.logoText}>CourtHub</Text>
                </View>

                {/* Header — centered */}
                <View style={styles.header}>
                    <Text style={styles.title}>Welcome back</Text>
                    <Text style={styles.subtitle}>Sign in to manage your sports venues</Text>
                </View>

                {/* Form */}
                <View style={styles.form}>

                    {/* Email */}
                    <View style={styles.fieldGroup}>
                        <Text style={styles.label}>EMAIL</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="Enter Email"
                            placeholderTextColor="#aab4c0"
                            value={email}
                            onChangeText={setEmail}
                            keyboardType="email-address"
                            autoCapitalize="none"
                            autoCorrect={false}
                        />
                    </View>

                    {/* Password */}
                    <View style={styles.fieldGroup}>
                        <View style={styles.labelRow}>
                            <Text style={styles.label}>PASSWORD</Text>
                            <TouchableOpacity>
                                <Text style={styles.forgotText}>FORGOT PASSWORD?</Text>
                            </TouchableOpacity>
                        </View>
                        <View style={styles.passwordContainer}>
                            <TextInput
                                style={styles.passwordInput}
                                placeholder="Enter Password"
                                placeholderTextColor="#aab4c0"
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
                                    color="#94a3b8"
                                />
                            </TouchableOpacity>
                        </View>
                    </View>

                    {/* Sign In Button */}
                    <TouchableOpacity
                        style={[styles.signInBtn, loading && styles.signInBtnDisabled]}
                        onPress={handleLogin}
                        disabled={loading}
                        activeOpacity={0.88}
                    >
                        {loading ? (
                            <ActivityIndicator color="#fff" />
                        ) : (
                            <Text style={styles.signInText}>Sign In  →</Text>
                        )}
                    </TouchableOpacity>

                    {/* OR Divider */}
                    <View style={styles.dividerRow}>
                        <View style={styles.dividerLine} />
                        <Text style={styles.dividerText}>OR</Text>
                        <View style={styles.dividerLine} />
                    </View>

                    {/* OTP Button */}
                    <TouchableOpacity
                        style={styles.otpBtn}
                        activeOpacity={0.85}
                        onPress={handleOTPLogin}
                        disabled={loading}
                    >
                        <View style={styles.otpIconBox}>
                            <MaterialIcons name="dialpad" size={15} color="#fff" />
                        </View>
                        <Text style={styles.otpText}>Sign in with OTP Code</Text>
                    </TouchableOpacity>
                </View>

                {/* Footer */}
                <View style={styles.footer}>
                    <Text style={styles.footerText}>New to CourtHub? </Text>
                    <TouchableOpacity onPress={() => router.push('/(auth)/signup')}>
                        <Text style={styles.createAccountText}>Create account</Text>
                    </TouchableOpacity>
                </View>
            </ScrollView>
        </KeyboardAvoidingView>
    );
}

const GREEN = Colors.primary;

const styles = StyleSheet.create({
    flex: { flex: 1, backgroundColor: '#fff' },
    container: {
        flexGrow: 1,
        paddingHorizontal: 24,
        paddingTop: 56,
        paddingBottom: 40,
        backgroundColor: '#fff',
    },

    // Logo — centered
    logoContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        marginBottom: 40,
    },
    logoIcon: {
        width: 38,
        height: 38,
        borderRadius: 10,
        backgroundColor: GREEN,
        alignItems: 'center',
        justifyContent: 'center',
    },
    logoText: {
        fontSize: 20,
        fontWeight: '800',
        color: '#0f172a',
        letterSpacing: -0.3,
    },

    // Header — centered
    header: {
        alignItems: 'center',
        marginBottom: 36,
    },
    title: {
        fontSize: 32,
        fontWeight: '800',
        color: '#0f172a',
        letterSpacing: -0.5,
        marginBottom: 6,
        textAlign: 'center',
    },
    subtitle: {
        fontSize: 14,
        color: '#64748b',
        textAlign: 'center',
    },

    // Form
    form: { gap: 18 },
    fieldGroup: { gap: 5 },
    label: {
        fontSize: 11,
        fontWeight: '700',
        color: '#94a3b8',
        letterSpacing: 0.8,
    },
    labelRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    input: {
        height: 50,
        backgroundColor: '#f1f5f9',
        borderRadius: 10,
        paddingHorizontal: 16,
        fontSize: 15,
        color: '#0f172a',
    },
    forgotText: {
        fontSize: 10,
        fontWeight: '800',
        color: GREEN,
        letterSpacing: 0.5,
    },
    passwordContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#f1f5f9',
        borderRadius: 10,
        height: 50,
    },
    passwordInput: {
        flex: 1,
        paddingHorizontal: 16,
        fontSize: 15,
        color: '#0f172a',
    },
    eyeBtn: { padding: 12 },

    // Sign In Button
    signInBtn: {
        height: 52,
        borderRadius: 12,
        backgroundColor: GREEN,
        alignItems: 'center',
        justifyContent: 'center',
        marginTop: 4,
        // Premium Shadow
        shadowColor: GREEN,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.25,
        shadowRadius: 8,
        elevation: 4,
    },
    signInBtnDisabled: { opacity: 0.6 },
    signInText: {
        fontSize: 16,
        fontWeight: '700',
        color: '#fff',
        letterSpacing: 0.2,
    },

    // OR divider
    dividerRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        marginVertical: 2,
    },
    dividerLine: { flex: 1, height: 1, backgroundColor: '#e2e8f0' },
    dividerText: {
        fontSize: 12,
        fontWeight: '600',
        color: '#94a3b8',
    },

    // OTP button
    otpBtn: {
        height: 52,
        borderRadius: 12,
        borderWidth: 1.5,
        borderColor: '#e2e8f0',
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        backgroundColor: '#fff',
        // Subtle Shadow
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 1,
    },
    otpIconBox: {
        width: 24,
        height: 24,
        borderRadius: 5,
        backgroundColor: GREEN,
        alignItems: 'center',
        justifyContent: 'center',
    },
    otpText: {
        fontSize: 15,
        fontWeight: '600',
        color: '#0f172a',
    },

    // Footer
    footer: {
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        marginTop: 40,
    },
    footerText: { fontSize: 14, color: '#64748b' },
    createAccountText: { fontSize: 14, fontWeight: '700', color: GREEN },
});
