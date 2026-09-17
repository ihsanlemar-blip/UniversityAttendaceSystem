'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Languages, Check } from 'lucide-react';
import { useLanguage } from '../../context/language-context';
import { SUPPORTED_LOCALES, SupportedLocale } from '../../lib/i18n/types';

export function LanguageSelector({ variant = 'default' }: { variant?: 'default' | 'compact' }) {
  const { locale, setLocale } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const toggleDropdown = () => setIsOpen((prev) => !prev);

  // Close dropdown on outside click or Escape
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const currentConfig = SUPPORTED_LOCALES[locale];

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        type="button"
        onClick={toggleDropdown}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={`Select language. Current language: ${currentConfig.name}`}
        className={`inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition ${
          variant === 'compact' ? 'px-2 py-1' : ''
        }`}
      >
        <Languages className="w-3.5 h-3.5 text-slate-500 shrink-0" aria-hidden="true" />
        <span className="font-medium">{currentConfig.nativeName}</span>
      </button>

      {isOpen && (
        <div
          role="listbox"
          aria-label="Available languages"
          className="absolute end-0 mt-1.5 w-44 rounded-xl bg-white p-1 shadow-lg ring-1 ring-black/5 z-50 focus:outline-none animate-in fade-in zoom-in-95 duration-100"
        >
          {Object.values(SUPPORTED_LOCALES).map((item) => {
            const isSelected = item.code === locale;
            return (
              <button
                key={item.code}
                role="option"
                aria-selected={isSelected}
                onClick={() => {
                  setLocale(item.code as SupportedLocale);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-lg text-left transition ${
                  isSelected
                    ? 'bg-indigo-50 text-indigo-700 font-bold'
                    : 'text-slate-700 hover:bg-slate-100 font-medium'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span>{item.nativeName}</span>
                  <span className="text-[11px] text-slate-400">({item.name})</span>
                </div>
                {isSelected && <Check className="w-3.5 h-3.5 text-indigo-600 shrink-0" aria-hidden="true" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
