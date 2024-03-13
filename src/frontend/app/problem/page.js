"use client";

import styles from "./page.module.css";

export default function Content() {
  async function onSubmit(event) {
    event.preventDefault();
 
    const formData = new FormData(event.target);
    const response = await fetch("http://127.0.0.1:8080/api/home", {
      method: "POST",
      body: formData
    });
    const data = await response.json();
  }

  return (
    <main className={styles.main}>
      <form className={styles.form} onSubmit={onSubmit} enctype="multipart/form-data">
        <label className={styles.label}>
          Problem Type:
          <select name="problemType" className={styles.select}>
            <option value="">Select problem type</option>
            <option value="solver">Solver</option>
            <option value="optimizer">Optimizer</option>
            <option value="coverage">Coverage</option>
          </select>
        </label>
        
        <label className={styles.label} id='file'>
          File(s):
          <input type="file" name="file" multiple className={styles.fileupload} />
        </label>

        <label className={styles.label}>
          Variables:
          <input type="text" name="variables" className={styles.input} />
        </label>

        <label className={styles.label}>
          Objective:
          <select name="objective" className={styles.select}>
            <option value="">Select objective type</option>
            <option value="minimize">Minimize</option>
            <option value="maximize">Maximize</option>
          </select>
        </label>

        <label className={styles.label}>
          Constraints:
          <input type="text" name="constraints" className={styles.input} />
        </label>

        <button type="submit" className={styles.button}>Submit</button>
      </form>
    </main>
  );
}