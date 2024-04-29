import styles from "./page.module.css";

export default function Content() {
  return (
    <main className={styles.main}>
      <div>
        <div className={styles.section}>
          <h1>FAQ</h1>
        </div>

        <div id="about-project" className={styles.section}>
          <h1>About the project</h1>
        </div>

        <div className={styles.question}>
          <h1># What is Gurobi Wrapper?</h1>
          <p>Gurobi Wrapper is a lightweight wrapper for <a href="https://www.gurobi.com">Gurobi Optimizer</a> designed to simplify the ETL pipeline process for simple Market Optimization tasks.</p>
        </div>

        <div className={styles.question}>
          <h1># What is Gurobi Optimizer?</h1>
          <p><a href="https://www.gurobi.com">Gurobi Optimizer</a> is a solver which uses mathematical optimization to derive answers to mixed-integer linear programming problems.</p>
        </div>

        <div className={styles.question}>
          <h1># Where can the source code be found?</h1>
          <p>The source code is hosted <a href="https://github.com/rileyounga/GurobiETL">on Github</a>.</p>
        </div>

        <div className={styles.question}>
          <h1># Which problems are supported by Gurobi Wrapper?</h1>
          <p>Presently, we support portfolio optimization, mathematical optimization, and location analysis. For more information about each problem and the wrapper's capabilities, see the corresponding subsection in the <a href="#about-problems">about problems</a> section.</p>
        </div>


        <div id="about-problems" className={styles.section}>
          <h1>About problems</h1>
        </div>

        <div className={styles.question}>
          <h1># Portfolio optimization</h1>
          <p>The portfolio optimization problem takes a list of stock ticker values from a file and optimizes a portfolo based on the expected return and volatility of the stocks.</p>
          <p>After running a portfolio optimization problem, the dashboard will present a card detailing a portfolio of stocks which minimizes risk. Additionally, a visualization of the problem is displayed on a chart.</p>
        </div>

        <div className={styles.question}>
          <h1># Mathematical optimization</h1>
          <p>The mathematical optimization problem takes objectives, variables, and constraints and returns an optimal set of decisions.</p>
        </div>

        <div className={styles.question}>
          <h1># Location analysis</h1>
          <p>Location analysis problems seeks an optimal placement of facilities. Here, finding the "optimal" solution can involve minimizing factors like transportation costs or considering how facility placements might encroach upon residential housing.</p>
        </div>


        <div id="usage" className={styles.section}>
          <h1>Using the tool</h1>
        </div>

        <div className={styles.question}>
          <h1># Problem setup</h1>
          <p>Problems can be defined under the "Problem" tab in the navigation bar. Problem construction is fairly straightforward, though clarification on some points could prove useful:</p>
          <ul>
            <li>The file selection tool allows multi-file selection.</li>
            <li>By default, the parameters, variables, and constraints sections each have one empty field. Empty fields are ignored when the problem is run. If more fields are needed, use the button beneath the fields. The buttons marked "X" beside each field will remove the neighboring field.</li>
            <li>The "Run problem" button at the bottom of the page will run the selected problem type using the fields and files provided.</li>
            <li>Upon running a problem, the user will be redirected to a dashboard which presents the results of the analysis.</li>
          </ul>
        </div>

        <div className={styles.question}>
          <h1># Dashboard</h1>
          <p>If a problem has been run, the dashboard will display analysis results. Otherwise, a link to the problem tab will be displayed.</p>
        </div>
      </div>
    </main>
  );
}
