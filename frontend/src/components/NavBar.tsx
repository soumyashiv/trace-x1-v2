"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export default function NavBar() {
  const pathname = usePathname();
  const router = useRouter();

  const linkClass = (href: string) =>
    `px-3 py-1.5 rounded-md text-sm ${
      pathname === href ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"
    }`;

  function logout() {
    window.localStorage.removeItem("tracex_token");
    router.push("/login");
  }

  return (
    <nav className="flex items-center justify-between px-6 py-3 border-b border-slate-800">
      <div className="flex items-center gap-6">
        <span className="font-bold tracking-tight text-lg">
          TRACE<span className="text-red-500">-X</span>
        </span>
        <Link href="/dashboard" className={linkClass("/dashboard")}>
          Cases
        </Link>
        <Link href="/cases/new" className={linkClass("/cases/new")}>
          New Investigation
        </Link>
        <Link href="/settings" className={linkClass("/settings")}>
          Settings
        </Link>
      </div>
      <button onClick={logout} className="text-sm text-slate-400 hover:text-white">
        Log out
      </button>
    </nav>
  );
}
