import { useState, useRef, useEffect } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import {
    View, Text, TextInput, TouchableOpacity,
    Alert, ActivityIndicator, StyleSheet, StatusBar, KeyboardAvoidingView, Platform,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { Colors } from '@/src/theme/colors';
import { verifyCode, requestCode, loginVerifyCode, loginRequestCode } from '@/src/api/auth';
import { useAuthStore } from '@/src/store/auth';

const OTP_LENGTH = 6;

export default function VerifyScreen() {
    const { email, mode = 'signup' } = useLocalSearchParams<{ email: string; mode?: 'signup' | 'login' }>();
    const [otp, setOtp] = useState<string[]>(Array(OTP_LENGTH).fill(''));
    const [loading, setLoading] = useState(false);
    const [resending, setResending] = useState(false);
    const [countdown, setCountdown] = useState(60);
    const inputs = useRef<(TextInput | null)[]>([]);
    const { setAuth } = useAuthStore();

    // Countdown timer for resend button
    useEffect(() => {
        if (countdown <= 0) return;
        const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
        return () => clearTimeout(timer);
    }, [countdown]);

    const handleChange = (text: string, index: number) => {
        // Allow paste of full OTP
        if (text.length > 1) {
            const digits = text.replace(/\D/g, '').slice(0, OTP_LENGTH).split('');
            const next = [...otp];
            digits.forEach((d, i) => { if (index + i < OTP_LENGTH) next[index + i] = d; });
            setOtp(next);
            const nextIndex = Math.min(index + digits.length, OTP_LENGTH - 1);
            inputs.current[nextIndex]?.focus();
            return;
        }

        const digit = text.replace(/\D/g, '');
        const next = [...otp];
        next[index] = digit;
        setOtp(next);
        if (digit && index < OTP_LENGTH - 1) inputs.current[index + 1]?.focus();
    };

    const handleKeyPress = (e: any, index: number) => {
        if (e.nativeEvent.key === 'Backspace' && !otp[index] && index > 0) {
            inputs.current[index - 1]?.focus();
        }
    };

    const handleVerify = async () => {
        const code = otp.join('');
        if (code.length < OTP_LENGTH) {
            Alert.alert('Incomplete', 'Please enter all 6 digits.');
            return;
        }
        try {
            setLoading(true);
            const data = mode === 'signup'
                ? await verifyCode(email!, code)
                : await loginVerifyCode(email!, code);

            if (data.success && data.data?.access_token) {
                await setAuth(data.data.access_token, {
                    name: data.data.name || '',
                    email: email!
                });
                router.replace('/(owner)/dashboard');
            } else {
                Alert.alert('Verification Failed', data.message || 'Invalid or expired code.');
            }
        } catch (error: any) {
            const msg = error.response?.data?.message || error.message || 'Verification failed';
            Alert.alert('Error', msg);
        } finally {
            setLoading(false);
        }
    };

    const handleResend = async () => {
        if (countdown > 0) return;
        try {
            setResending(true);
            if (mode === 'signup') {
                await requestCode(email!);
            } else {
                await loginRequestCode(email!);
            }
            setCountdown(60);
            Alert.alert('Sent!', 'A new code has been sent to your email.');
        } catch (error: any) {
            Alert.alert('Error', 'Could not resend code. Please try again.');
        } finally {
            setResending(false);
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.flex}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
            <StatusBar barStyle="dark-content" backgroundColor={Colors.white} />

            {/* Header */}
            <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
                <MaterialIcons name="arrow-back" size={22} color={Colors.gray700} />
            </TouchableOpacity>

            <View style={styles.content}>
                {/* Icon */}
                <View style={styles.iconContainer}>
                    <MaterialIcons name="mark-email-unread" size={48} color={Colors.primary} />
                </View>

                <Text style={styles.title}>Check Your Email</Text>
                <Text style={styles.subtitle}>
                    We sent a 6-digit verification code to
                </Text>
                <Text style={styles.email}>{email}</Text>

                {/* OTP Inputs */}
                <View style={styles.otpRow}>
                    {otp.map((digit, i) => (
                        <TextInput
                            key={i}
                            ref={ref => { inputs.current[i] = ref; }}
                            style={[styles.otpInput, digit ? styles.otpInputFilled : null]}
                            value={digit}
                            onChangeText={text => handleChange(text, i)}
                            onKeyPress={e => handleKeyPress(e, i)}
                            keyboardType="number-pad"
                            maxLength={OTP_LENGTH}
                            selectTextOnFocus
                            textAlign="center"
                            accessibilityLabel={`OTP digit ${i + 1}`}
                        />
                    ))}
                </View>

                {/* Verify Button */}
                <TouchableOpacity
                    style={[styles.verifyBtn, loading && styles.verifyBtnDisabled]}
                    onPress={handleVerify}
                    disabled={loading}
                    activeOpacity={0.88}
                >
                    {loading
                        ? <ActivityIndicator color={Colors.white} />
                        : <Text style={styles.verifyBtnText}>Verify & Continue</Text>
                    }
                </TouchableOpacity>

                {/* Resend */}
                <View style={styles.resendRow}>
                    <Text style={styles.resendText}>Didn't receive the code? </Text>
                    <TouchableOpacity onPress={handleResend} disabled={countdown > 0 || resending}>
                        {resending
                            ? <ActivityIndicator size="small" color={Colors.primary} />
                            : <Text style={[styles.resendLink, countdown > 0 && styles.resendLinkDisabled]}>
                                {countdown > 0 ? `Resend in ${countdown}s` : 'Resend'}
                            </Text>
                        }
                    </TouchableOpacity>
                </View>

                <Text style={styles.hint}>Check your spam folder if you don't see it.</Text>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    flex: { flex: 1, backgroundColor: Colors.white },
    backBtn: {
        position: 'absolute', top: 52, left: 20, zIndex: 10,
        width: 40, height: 40, borderRadius: 20,
        backgroundColor: Colors.gray100,
        alignItems: 'center', justifyContent: 'center',
    },
    content: {
        flex: 1, alignItems: 'center', justifyContent: 'center',
        paddingHorizontal: 28, paddingBottom: 40,
    },
    iconContainer: {
        width: 88, height: 88, borderRadius: 44,
        backgroundColor: Colors.primaryBg,
        alignItems: 'center', justifyContent: 'center',
        marginBottom: 24,
    },
    title: {
        fontSize: 26, fontWeight: '800', color: Colors.gray900,
        textAlign: 'center', marginBottom: 10,
    },
    subtitle: { fontSize: 14, color: Colors.gray500, textAlign: 'center' },
    email: {
        fontSize: 14, fontWeight: '700', color: Colors.primary,
        textAlign: 'center', marginTop: 4, marginBottom: 32,
    },

    // OTP
    otpRow: { flexDirection: 'row', gap: 10, marginBottom: 32 },
    otpInput: {
        width: 46, height: 54,
        backgroundColor: Colors.gray100,
        borderRadius: 12,
        fontSize: 22, fontWeight: '700', color: Colors.gray900,
        borderWidth: 2, borderColor: 'transparent',
    },
    otpInputFilled: {
        borderColor: Colors.primary, backgroundColor: Colors.primaryBg,
    },

    // Button
    verifyBtn: {
        width: '100%', height: 54, borderRadius: 16,
        backgroundColor: Colors.primary,
        alignItems: 'center', justifyContent: 'center',
        shadowColor: Colors.primary, shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.3, shadowRadius: 10, elevation: 5,
        marginBottom: 20,
    },
    verifyBtnDisabled: { opacity: 0.6 },
    verifyBtnText: { fontSize: 16, fontWeight: '700', color: Colors.white },

    // Resend
    resendRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
    resendText: { fontSize: 14, color: Colors.gray500 },
    resendLink: { fontSize: 14, fontWeight: '700', color: Colors.primary },
    resendLinkDisabled: { color: Colors.gray400 },
    hint: { fontSize: 12, color: Colors.gray400, textAlign: 'center' },
});
