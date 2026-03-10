import { apiClient } from './client';
import { getProperties } from './properties';

/** Fetch all courts across all owner properties by aggregating per-property calls */
export const getCourts = async () => {
    // First get all properties
    const propsRes = await getProperties();
    const properties: { id: number; name: string }[] = propsRes?.data ?? [];

    // Then fetch courts for each property in parallel
    const courtArrays = await Promise.all(
        properties.map(async (prop) => {
            try {
                const res = await apiClient.get(`/properties/${prop.id}/courts`);
                const courts: any[] = res.data?.data ?? [];
                // Attach property_name for display
                return courts.map((c: any) => ({ ...c, property_name: prop.name }));
            } catch {
                return [];
            }
        })
    );

    const allCourts = courtArrays.flat();
    return { success: true, data: allCourts };
};

export const getCourt = async (id: number) => {
    const response = await apiClient.get(`/courts/${id}`);
    return response.data;
};

export const deleteCourt = async (id: number) => {
    const response = await apiClient.delete(`/courts/${id}`);
    return response.data;
};
