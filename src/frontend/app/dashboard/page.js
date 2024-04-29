"use client";
import styles from "./page.module.css";
import Image from "next/image";

export default function Content() {
  let solution = JSON.parse(localStorage.getItem("solution"));
  
  if (solution == null) {
    return (
      <main className={styles.main}>
        <a href="/problem">Define a problem</a>
      </main>
    );
  }
  else {
    let result = solution.result.split('\n');
    return (
      <main className={styles.main}>
          <div className={styles.grid}>
            { result &&
            <div className={styles.chart}>
              <h2>{result[1]}</h2>
              {result.slice(2).map((line) => (
                <p>{line}</p>
              ))}
            </div>
            }
            
            { solution["fig"] &&
            <div className={styles.chart}>
              <h2>Visualization:</h2>
                <Image
                  id="figure"
                  src={"data:image/png;base64," + solution.fig}
                  sizes="100vw"
                  style={{
                          width: '100%',
                          height: 'auto'
                        }}
                  width={2000}
                  height={1600}
                />
            </div>
            }

          </div>
      </main>
  );
  }
}
