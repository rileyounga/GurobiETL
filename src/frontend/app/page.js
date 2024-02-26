import styles from "./page.module.css";

export default function Content() {
  return (
    <main className={styles.main}>
      <div className={styles.center}>
        <h1>Gurobi Wrapper</h1>
      </div>
      
      <div className={styles.grid}>
        <a href="/dashboard" className={styles.card}>
          <h2>Dashboard</h2>
          <p>View output from the Gurobi API.</p>
        </a>

        <a href="/problem" className={styles.card}>
          <h2>Problem</h2>
          <p>Set up a MILP problem</p>
        </a>

        <a href="/faq" className={styles.card}>
          <h2>FAQ</h2>
          <p>Learn about the tool</p>
        </a>
      </div>
    </main>
  );
}
