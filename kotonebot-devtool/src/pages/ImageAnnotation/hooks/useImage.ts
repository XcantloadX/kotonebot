import { useState, useEffect } from 'react';

/**
 * A hook for processing an image from a URL.
 * It handles the loading of the image and returns the HTMLImageElement.
 * @param imageUrl The URL of the image to process.
 * @returns The loaded HTMLImageElement, or null if not loaded yet.
 */
export function useImage(imageUrl: string): HTMLImageElement | null {
    const [image, setImage] = useState<HTMLImageElement | null>(null);

    useEffect(() => {
        if (!imageUrl) {
            setImage(null);
            return;
        }

        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
            setImage(img);
        };
        img.onerror = () => {
            console.error(`Failed to load image from: ${imageUrl}`);
            setImage(null);
        };
        img.src = imageUrl;

        // Cleanup function
        return () => {
            img.onload = null;
            img.onerror = null;
        };
    }, [imageUrl]);

    return image;
}
