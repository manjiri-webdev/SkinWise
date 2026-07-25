import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./src/app/**/*.{js,ts,jsx,tsx}",
        "./src/components/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                pink: "#F1A4AF",
                pinkHover: "#DF7F8D",
                pinkSoft: "#F9E5E5",

                green: "#A7B682",
                greenHover: "#91A461",
                greenSoft: "#EBEEE3",

                lavender: "#B9A6DE",
                lavenderHover: "#9C81D0",
                lavenderSoft: "#D6CBEC",

                cream: "#FAF7F5",
                creamGradient1: "#FFFDFC",
                creamGradient2: "#F2ECE7",

                bg1 :"#F6ECEC",

                textDark: "#141414",
                textSecondary: "#2D2D2D",
                textTertiary: "#474747",

                divider: "#7D7774",
                danger: "#E76F51",
                success: "#6CBF84",
                warning: "#F4B860",
            },
            fontFamily: {
                display: ["var(--font-display)", "serif"],
                sans: ["var(--font-sans)", "system-ui", "sans-serif"],
            },
            borderRadius: {
                blob: "48px",
                card: "32px",
            },
            boxShadow: {
                floaty: "0 24px 60px -12px rgba(217,133,169,0.28)",
                soft: "0 8px 24px rgba(0,0,0,0.05)",
            },

        },
    },
    plugins: [],

};


export default config;