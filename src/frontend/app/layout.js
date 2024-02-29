import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from './navbar.js';


const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "Gurobi Wrapper",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Navbar />
        {children}
      </body>
    </html>
  );
}
