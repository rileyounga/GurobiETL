"use client";

import { usePathname } from 'next/navigation';
import styles from "./navbar.module.css"

const tabs = [
  { name: 'Home', href: '/' },
  { name: 'Dashboard', href: '/dashboard' },
  { name: 'Problem', href: '/problem' },
  { name: 'FAQ', href: '/faq' },
];

export default function Navbar() {
  const path = usePathname();

  return (
    <div className={styles.main}>
      <div className={styles.bar}>
        {tabs.map((item) => (
            <a key={item.name} className={path === item.href ? styles.tabsel : styles.tab} href={item.href}>{item.name}</a>
        ))}
      </div>
    </div>
  );
}
