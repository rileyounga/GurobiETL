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
    return (
      <main className={styles.main}>
          <div className={styles.grid}>
            { solution["result"] &&
            <div className={styles.chart}>
              <h2>Result:</h2>
              <table>
                <tr>
                  {Object.keys(solution["result"][0]).map((col) => (
                    <td>{col}</td>
                  ))}
                </tr>
                {solution["result"].map((line) => (
                  <tr>
                    {Object.values(line).map((val) => (
                      <td>{val}</td>
                    ))}
                  </tr>
                ))}
              </table>
            </div>
            }
            
            { solution["fig"] &&
            solution["fig"].map((image, index) => (
              <div className={styles.chart}>
                <h2>Visualization {index+1}:</h2>
                <Image
                  id="figure"
                  src={"data:image/png;base64," + image}
                  sizes="100vw"
                  style={{
                    width: '75%',
                    height: 'auto'
                  }}
                  width={2000}
                  height={1600}
                />
              </div>
            ))}

          </div>
      </main>
  );
  }
}
