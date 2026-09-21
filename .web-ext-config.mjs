export default {
  // Keep release packages lean: only the add-on itself.
  ignoreFiles: [
    "screenshots",
    "screenshots/**",
    "tools",
    "tools/**",
    "web-ext-artifacts",
    "web-ext-artifacts/**",
    ".gitignore",
    ".web-ext-config.mjs",
  ],
};
