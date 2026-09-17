import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  site: "https://galdes.github.io",
  base: "/central-de-ofertas",
  trailingSlash: "ignore",
  vite: {
    plugins: [tailwindcss()],
  },
});
