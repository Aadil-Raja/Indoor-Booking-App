import { useEffect } from 'react';
import { Redirect } from 'expo-router';
import { Box } from '@/components/ui/box';
import { Spinner } from '@/components/ui/spinner';
import { useAuthStore } from '@/src/store/auth';

export default function Index() {
    const { token, isLoading, checkAuth } = useAuthStore();

    useEffect(() => {
        checkAuth();
    }, []);

    if (isLoading) {
        return (
            <Box className="flex-1 bg-background-0 dark:bg-background-950 justify-center items-center">
                <Spinner size="large" />
            </Box>
        );
    }

    // Route to the dashboard if authenticated, otherwise to login.
    if (token) {
        return <Redirect href="/(owner)/dashboard" />;
    }

    return <Redirect href="/(auth)/login" />;
}
