import nextConfig from 'eslint-config-next';

const eslintConfig = [
  {
    ignores: [".next/**", "node_modules/**", "build/**"],
  },
  ...nextConfig,
];

export default eslintConfig;
