import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="w-full border-b bg-white shadow-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <Link href="/" className="text-2xl font-bold text-indigo-600 hover:text-indigo-500">
            Booml
          </Link>
          
          <nav className="hidden md:flex items-center gap-6">
            <Link href="/catalog" className="text-sm font-medium text-gray-700 hover:text-indigo-600">
              Каталог
            </Link>
            
            {/* Polygon link: Visible only to teachers */}
            {user?.role === 'TEACHER' && (
              <Link href="/polygon" className="text-sm font-medium text-gray-700 hover:text-indigo-600">
                Полигон
              </Link>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-4">
          {user ? (
            <>
              {/* 'My Courses' Button */}
              <Link 
                href="/my-courses"
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
              >
                Мои курсы
              </Link>

              <div className="hidden md:flex items-center gap-4 border-l pl-4">
                <span className="text-sm text-gray-700">{user.name}</span>
                <button 
                  onClick={logout}
                  className="text-sm font-medium text-gray-500 hover:text-red-600"
                >
                  Выйти
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-4">
              <Link href="/login" className="text-sm font-medium text-gray-700 hover:text-indigo-600">
                Войти
              </Link>
              <Link 
                href="/register" 
                className="rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-200"
              >
                Регистрация
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
