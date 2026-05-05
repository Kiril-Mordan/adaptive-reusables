# 02. Benchmark: Math Reasoning


- Date: 2026-05-05
- Status: draft



```python

```




    {'runs': 75, 'completed_runs': 74, 'task_count': 15, 'tasks_solved_once': 15}



## Intro

This benchmark tests WAA on deterministic math tasks where the difficulty comes from workflow synthesis rather than ambiguous answers. The useful question is whether WAA can consistently assemble and reuse the right workflow for a small but varied math task set.


## Benchmark Cases

The benchmark cases fall into four small groups:

- **Direct arithmetic**: tasks where one tool or one obvious two-step workflow should be enough.
- **Compositional arithmetic**: tasks that require combining several primitive tools in a fixed order.
- **Symbolic calculus and trigonometry**: tasks that depend on derivative or trig identities.
- **Stress cases**: tasks where the planner has to reconstruct a familiar formula from the available tool set.

One small caveat is worth calling out. `task_8` (`sin(x)^2 + cos(x)^2`) has the same expected output for every input because the identity always evaluates to `1`. That makes it useful as an identity-recognition case, but weak as a pure composition test: a degenerate workflow that returns a constant can still pass numerically.


### Direct Arithmetic



```python

```

    task_1
    Add left and right and return the result as a single scalar value.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>left</th>
      <th>right</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>2.00</td>
      <td>5.00</td>
      <td>7.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>-3.00</td>
      <td>10.00</td>
      <td>7.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>1.50</td>
      <td>2.50</td>
      <td>4.0</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>0.00</td>
      <td>7.00</td>
      <td>7.0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>-8.00</td>
      <td>-2.00</td>
      <td>-10.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>9.00</td>
      <td>1.00</td>
      <td>10.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>100.00</td>
      <td>0.50</td>
      <td>100.5</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>12.00</td>
      <td>-2.00</td>
      <td>10.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>3.25</td>
      <td>4.75</td>
      <td>8.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>-1.25</td>
      <td>1.25</td>
      <td>0.0</td>
    </tr>
  </tbody>
</table>
</div>


    task_2
    Subtract right from left and return the difference.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>left</th>
      <th>right</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>7.00</td>
      <td>2.00</td>
      <td>5.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>5.00</td>
      <td>5.00</td>
      <td>0.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>-4.00</td>
      <td>3.00</td>
      <td>-7.0</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>9.50</td>
      <td>1.50</td>
      <td>8.0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>0.00</td>
      <td>2.00</td>
      <td>-2.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>20.00</td>
      <td>-2.00</td>
      <td>22.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>-8.00</td>
      <td>-3.00</td>
      <td>-5.0</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>4.25</td>
      <td>0.25</td>
      <td>4.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>3.00</td>
      <td>9.00</td>
      <td>-6.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>100.00</td>
      <td>33.00</td>
      <td>67.0</td>
    </tr>
  </tbody>
</table>
</div>


    task_3
    Multiply left and right and return the product.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>left</th>
      <th>right</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>3.0</td>
      <td>4.0</td>
      <td>12.00</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>-2.0</td>
      <td>5.0</td>
      <td>-10.00</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>1.5</td>
      <td>2.0</td>
      <td>3.00</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>0.0</td>
      <td>10.0</td>
      <td>0.00</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>-3.0</td>
      <td>-7.0</td>
      <td>21.00</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>8.0</td>
      <td>0.5</td>
      <td>4.00</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>12.0</td>
      <td>3.0</td>
      <td>36.00</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>9.0</td>
      <td>-1.0</td>
      <td>-9.00</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>2.5</td>
      <td>2.5</td>
      <td>6.25</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>11.0</td>
      <td>11.0</td>
      <td>121.00</td>
    </tr>
  </tbody>
</table>
</div>


    task_4
    Divide left by right and return the quotient.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>left</th>
      <th>right</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>8.0</td>
      <td>2.0</td>
      <td>4.00</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>9.0</td>
      <td>3.0</td>
      <td>3.00</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>7.5</td>
      <td>2.5</td>
      <td>3.00</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>-12.0</td>
      <td>4.0</td>
      <td>-3.00</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>1.0</td>
      <td>4.0</td>
      <td>0.25</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>100.0</td>
      <td>5.0</td>
      <td>20.00</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>-9.0</td>
      <td>-3.0</td>
      <td>3.00</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>3.6</td>
      <td>1.2</td>
      <td>3.00</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>22.0</td>
      <td>11.0</td>
      <td>2.00</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>81.0</td>
      <td>9.0</td>
      <td>9.00</td>
    </tr>
  </tbody>
</table>
</div>


### Compositional Arithmetic



```python

```

    task_5
    First add left and right, then square the result.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>left</th>
      <th>right</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>2.00</td>
      <td>3.00</td>
      <td>25.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>-1.00</td>
      <td>4.00</td>
      <td>9.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>1.50</td>
      <td>0.50</td>
      <td>4.0</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>0.00</td>
      <td>7.00</td>
      <td>49.0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>-4.00</td>
      <td>-2.00</td>
      <td>36.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>10.00</td>
      <td>-1.00</td>
      <td>81.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>6.00</td>
      <td>6.00</td>
      <td>144.0</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>3.25</td>
      <td>1.75</td>
      <td>25.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>-8.00</td>
      <td>9.00</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>0.50</td>
      <td>0.50</td>
      <td>1.0</td>
    </tr>
  </tbody>
</table>
</div>


    task_6
    Compute (left + right) multiplied by (left - right).



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>left</th>
      <th>right</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>7.0</td>
      <td>2.00</td>
      <td>45.0000</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>5.0</td>
      <td>5.00</td>
      <td>0.0000</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>8.0</td>
      <td>3.00</td>
      <td>55.0000</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>1.5</td>
      <td>0.50</td>
      <td>2.0000</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>-4.0</td>
      <td>2.00</td>
      <td>12.0000</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>10.0</td>
      <td>-1.00</td>
      <td>99.0000</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>3.0</td>
      <td>1.00</td>
      <td>8.0000</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>12.0</td>
      <td>4.00</td>
      <td>128.0000</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>0.5</td>
      <td>0.25</td>
      <td>0.1875</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>-6.0</td>
      <td>-2.00</td>
      <td>32.0000</td>
    </tr>
  </tbody>
</table>
</div>


    task_7
    Return the distance between the two numbers on the real line.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>left</th>
      <th>right</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>10.00</td>
      <td>4.00</td>
      <td>6.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>-2.00</td>
      <td>5.00</td>
      <td>7.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>3.00</td>
      <td>3.00</td>
      <td>0.0</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>1.50</td>
      <td>2.50</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>-10.00</td>
      <td>-4.00</td>
      <td>6.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>7.00</td>
      <td>-1.00</td>
      <td>8.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>0.00</td>
      <td>9.00</td>
      <td>9.0</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>2.25</td>
      <td>0.25</td>
      <td>2.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>-8.00</td>
      <td>1.00</td>
      <td>9.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>4.00</td>
      <td>11.00</td>
      <td>7.0</td>
    </tr>
  </tbody>
</table>
</div>


    task_9
    Compute the geometric mean of two positive numbers by multiplying them first and then taking the square root.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>left</th>
      <th>right</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>4.00</td>
      <td>9.0</td>
      <td>6.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>1.00</td>
      <td>16.0</td>
      <td>4.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>2.25</td>
      <td>4.0</td>
      <td>3.0</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>3.00</td>
      <td>12.0</td>
      <td>6.0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>0.25</td>
      <td>4.0</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>6.00</td>
      <td>24.0</td>
      <td>12.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>5.00</td>
      <td>20.0</td>
      <td>10.0</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>1.50</td>
      <td>6.0</td>
      <td>3.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>10.00</td>
      <td>40.0</td>
      <td>20.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>2.00</td>
      <td>8.0</td>
      <td>4.0</td>
    </tr>
  </tbody>
</table>
</div>


    task_13
    Compute the normalized radius sqrt(a squared plus b squared) divided by the magnitude of c.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>a</th>
      <th>b</th>
      <th>c</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>3.0</td>
      <td>4.0</td>
      <td>-2.0</td>
      <td>2.5</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>5.0</td>
      <td>12.0</td>
      <td>13.0</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>8.0</td>
      <td>15.0</td>
      <td>-5.0</td>
      <td>3.4</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>6.0</td>
      <td>8.0</td>
      <td>10.0</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>1.5</td>
      <td>2.0</td>
      <td>-0.5</td>
      <td>5.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>7.0</td>
      <td>24.0</td>
      <td>5.0</td>
      <td>5.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>9.0</td>
      <td>12.0</td>
      <td>-3.0</td>
      <td>5.0</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>4.0</td>
      <td>3.0</td>
      <td>2.5</td>
      <td>2.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>10.0</td>
      <td>24.0</td>
      <td>-2.0</td>
      <td>13.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>0.6</td>
      <td>0.8</td>
      <td>0.5</td>
      <td>2.0</td>
    </tr>
  </tbody>
</table>
</div>


    task_14
    Build a cubic interaction score by adding a and b, cubing the result, and dividing by the magnitude of c.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>a</th>
      <th>b</th>
      <th>c</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>1.0</td>
      <td>2.0</td>
      <td>-3.0</td>
      <td>9.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>2.0</td>
      <td>1.0</td>
      <td>9.0</td>
      <td>3.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>3.0</td>
      <td>3.0</td>
      <td>-6.0</td>
      <td>36.0</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>0.5</td>
      <td>1.5</td>
      <td>2.0</td>
      <td>4.0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>-1.0</td>
      <td>4.0</td>
      <td>-3.0</td>
      <td>9.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>5.0</td>
      <td>-2.0</td>
      <td>3.0</td>
      <td>9.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>2.5</td>
      <td>2.5</td>
      <td>-5.0</td>
      <td>25.0</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>4.0</td>
      <td>1.0</td>
      <td>2.5</td>
      <td>50.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>6.0</td>
      <td>-3.0</td>
      <td>-9.0</td>
      <td>3.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>1.2</td>
      <td>0.8</td>
      <td>0.5</td>
      <td>16.0</td>
    </tr>
  </tbody>
</table>
</div>


### Symbolic Calculus and Trigonometry



```python

```

    task_8
    Compute sin(x)^2 plus cos(x)^2 for the provided x.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>x</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>0.000000</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>0.500000</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>1.200000</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>-0.700000</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>2.400000</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>1.047198</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>1.570796</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>3.000000</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>-2.500000</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>4.100000</td>
      <td>1.0</td>
    </tr>
  </tbody>
</table>
</div>


    task_10
    Return the derivative of x squared evaluated at x.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>x</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>4.00</td>
      <td>8.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>-1.50</td>
      <td>-3.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>0.00</td>
      <td>0.0</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>2.25</td>
      <td>4.5</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>-3.00</td>
      <td>-6.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>7.00</td>
      <td>14.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>0.50</td>
      <td>1.0</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>-8.00</td>
      <td>-16.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>10.00</td>
      <td>20.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>1.20</td>
      <td>2.4</td>
    </tr>
  </tbody>
</table>
</div>


    task_11
    Return the derivative of x cubed plus sine of x evaluated at x.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>x</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>2.000000</td>
      <td>11.583853</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>0.000000</td>
      <td>1.000000</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>-1.000000</td>
      <td>3.540302</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>1.500000</td>
      <td>6.820737</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>1.570796</td>
      <td>7.402203</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>-2.500000</td>
      <td>17.948856</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>3.000000</td>
      <td>26.010008</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>0.250000</td>
      <td>1.156412</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>-4.000000</td>
      <td>47.346356</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>5.000000</td>
      <td>75.283662</td>
    </tr>
  </tbody>
</table>
</div>


    task_15
    Compute tangent of x by dividing sine of x by cosine of x.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>x</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>0.25</td>
      <td>0.255342</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>0.50</td>
      <td>0.546302</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>1.00</td>
      <td>1.557408</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>-0.75</td>
      <td>-0.931596</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>1.20</td>
      <td>2.572152</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>-1.10</td>
      <td>-1.964760</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>0.90</td>
      <td>1.260158</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>-0.30</td>
      <td>-0.309336</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>0.70</td>
      <td>0.842288</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>-0.60</td>
      <td>-0.684137</td>
    </tr>
  </tbody>
</table>
</div>


### Stress Cases



```python

```

    task_12
    Multiply two positive numbers, but do it through logarithms and exponentiation rather than a direct multiply tool.



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>case</th>
      <th>left</th>
      <th>right</th>
      <th>output_value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>1</td>
      <td>2.00</td>
      <td>8.0</td>
      <td>16.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2</td>
      <td>1.50</td>
      <td>4.0</td>
      <td>6.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>3</td>
      <td>3.00</td>
      <td>9.0</td>
      <td>27.0</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4</td>
      <td>0.50</td>
      <td>6.0</td>
      <td>3.0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>5</td>
      <td>10.00</td>
      <td>2.0</td>
      <td>20.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>6</td>
      <td>4.00</td>
      <td>4.0</td>
      <td>16.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>7</td>
      <td>1.25</td>
      <td>8.0</td>
      <td>10.0</td>
    </tr>
    <tr>
      <th>7</th>
      <td>8</td>
      <td>7.00</td>
      <td>3.0</td>
      <td>21.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>9</td>
      <td>2.50</td>
      <td>2.0</td>
      <td>5.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>10</td>
      <td>12.00</td>
      <td>0.5</td>
      <td>6.0</td>
    </tr>
  </tbody>
</table>
</div>


## Results

The results below come from the benchmark run documented in this note. Each task was run five times. The most useful metrics here are how many reruns completed, how much retry pressure each task needed, and how large the resulting workflows were.

The workflow artifacts used in this note do not currently persist wall-clock runtime, so this section uses saved retry counts instead of average duration.



```python

```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>task_id</th>
      <th>runs</th>
      <th>completed_runs</th>
      <th>success_rate</th>
      <th>avg_test_retries</th>
      <th>avg_workflow_steps</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>task_1</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>2.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>task_10</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>2.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>task_11</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>4.4</td>
    </tr>
    <tr>
      <th>3</th>
      <td>task_12</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>1.2</td>
      <td>5.0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>task_13</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>1.6</td>
      <td>7.0</td>
    </tr>
    <tr>
      <th>5</th>
      <td>task_14</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>5.0</td>
    </tr>
    <tr>
      <th>6</th>
      <td>task_15</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>4.0</td>
    </tr>
    <tr>
      <th>7</th>
      <td>task_2</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>2.0</td>
    </tr>
    <tr>
      <th>8</th>
      <td>task_3</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>2.0</td>
    </tr>
    <tr>
      <th>9</th>
      <td>task_4</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>2.0</td>
    </tr>
    <tr>
      <th>10</th>
      <td>task_5</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>3.0</td>
    </tr>
    <tr>
      <th>11</th>
      <td>task_6</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>4.0</td>
    </tr>
    <tr>
      <th>12</th>
      <td>task_7</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>3.0</td>
    </tr>
    <tr>
      <th>13</th>
      <td>task_8</td>
      <td>5</td>
      <td>4</td>
      <td>0.8</td>
      <td>3.0</td>
      <td>1.2</td>
    </tr>
    <tr>
      <th>14</th>
      <td>task_9</td>
      <td>5</td>
      <td>5</td>
      <td>1.0</td>
      <td>0.0</td>
      <td>3.0</td>
    </tr>
  </tbody>
</table>
</div>




```python

```


    
![png](../workflow_auto_assembler_ipynb_cell14_out0.png)
    


## Example Workflows

A few saved workflows are worth showing directly. One from each group and one exception worth noting. 



```python

```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>task_id</th>
      <th>group</th>
      <th>workflow_id</th>
      <th>workflow_step_count</th>
      <th>test_retries</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>task_1</td>
      <td>Direct arithmetic</td>
      <td>9d418c7863d543959ae985642cbad0bb</td>
      <td>2</td>
      <td>0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>task_7</td>
      <td>Compositional arithmetic</td>
      <td>de5ac14d307940c99e97321f9b9e705a</td>
      <td>3</td>
      <td>0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>task_8</td>
      <td>Exception</td>
      <td>ff62880d4d93476fab5bb81802081a91</td>
      <td>2</td>
      <td>3</td>
    </tr>
    <tr>
      <th>3</th>
      <td>task_11</td>
      <td>Symbolic calculus and trigonometry</td>
      <td>b4ef5b22b358428f9582b51622c88a98</td>
      <td>4</td>
      <td>0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>task_12</td>
      <td>Stress cases</td>
      <td>a9eb4705d55b4cceaa691a927e0a935f</td>
      <td>5</td>
      <td>0</td>
    </tr>
  </tbody>
</table>
</div>




```python

```

    task_1: Add left and right and return the result as a single scalar value.
      1. add
    {
        "left": "0.output.left",
        "right": "0.output.right"
    }
      2. output_model
    {
        "value": "1.output.value"
    }
    
    task_7: Return the distance between the two numbers on the real line.
      1. subtract
    {
        "left": "0.output.left",
        "right": "0.output.right"
    }
      2. absolute_value
    {
        "x": "1.output.value"
    }
      3. output_model
    {
        "value": "2.output.value"
    }
    
    task_8: Compute sin(x)^2 plus cos(x)^2 for the provided x.
      1. divide
    {
        "left": "1",
        "right": "1"
    }
      2. output_model
    {
        "value": "1.output.value"
    }
    
    task_11: Return the derivative of x cubed plus sine of x evaluated at x.
      1. derivative_cube
    {
        "x": "0.output.x"
    }
      2. derivative_sine
    {
        "x": "0.output.x"
    }
      3. add
    {
        "left": "1.output.value",
        "right": "2.output.value"
    }
      4. output_model
    {
        "value": "3.output.value"
    }
    
    task_12: Multiply two positive numbers, but do it through logarithms and exponentiation rather than a direct multiply tool.
      1. natural_log
    {
        "x": "0.output.left"
    }
      2. natural_log
    {
        "x": "0.output.right"
    }
      3. add
    {
        "left": "1.output.value",
        "right": "2.output.value"
    }
      4. exponential
    {
        "x": "3.output.value"
    }
      5. output_model
    {
        "value": "4.output.value"
    }
    


## Conclusion

In this benchmark, all 15 tasks were run 5 times. 14 tasks completed in all 5 runs. `task_8` completed in 4 of 5 runs and remains the main exception in this set.

`task_8` is also defined in a way that lets the system in its current form exploit the test. Because all expected outputs are identical, the system can fill in the final answer directly instead of building the intended trig workflow. The numeric output is not necessarily wrong, but it is not the behavior this task was meant to reward.

This benchmark shows that, for this system, workflow composition is easier to trust when more than one test case is provided and the expected outputs vary across those cases. When every expected output is identical, a shortcut or overfitted answer may pass.

