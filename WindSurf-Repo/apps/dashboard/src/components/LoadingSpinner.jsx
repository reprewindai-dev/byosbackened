import React from 'react';

export default function LoadingSpinner({ size = 'md', centered = false }) {
  const sizeMap = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8', xl: 'w-12 h-12' };
  const spinner = (
    <div className={`${sizeMap[size] || sizeMap.md} border-2 border-gray-700 border-t-indigo-500 rounded-full animate-spin`} />
  );
  if (centered) {
    return <div className="flex items-center justify-center w-full h-full min-h-[120px]">{spinner}</div>;
  }
  return spinner;
}
