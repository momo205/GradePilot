export type MockClass = { id: string; title: string };

export const MOCK_CLASSES: MockClass[] = [
  { id: 'cs101', title: 'CS 101: Data Structures' },
  { id: 'bio200', title: 'BIO 200: Genetics' },
  { id: 'math220', title: 'MATH 220: Linear Algebra' },
  { id: 'eng150', title: 'ENG 150: Rhetoric' },
];

export const MOCK_TOPICS_BY_CLASS: Record<string, string[]> = {
  cs101: ['Arrays & Linked Lists', 'Stacks & Queues', 'Hash Tables', 'Binary Trees', 'Graph Traversal'],
  bio200: ['Mendelian Inheritance', 'DNA Replication', 'Gene Expression', 'Mutations', 'Population Genetics'],
  math220: ['Vector Spaces', 'Matrix Operations', 'Determinants', 'Eigenvalues', 'Orthogonality'],
  eng150: ['Thesis Construction', 'Ethos, Pathos, Logos', 'Counterargument', 'Citation Styles', 'Revision Strategy'],
};
