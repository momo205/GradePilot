'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, ChevronDown, Eye, EyeOff } from 'lucide-react';

const CLASSES = [
  'CS 101: Data Structures',
  'BIO 200: Genetics',
  'MATH 220: Linear Algebra',
];

const TOPICS: Record<string, string[]> = {
  'CS 101: Data Structures': ['Arrays & Linked Lists', 'Trees & Graphs', 'Sorting Algorithms', 'Dynamic Programming'],
  'BIO 200: Genetics': ['Mitosis & Meiosis', 'DNA Replication', 'Mendelian Genetics', 'Gene Expression'],
  'MATH 220: Linear Algebra': ['Vectors & Matrices', 'Eigenvalues & Eigenvectors', 'Linear Transformations', 'Determinants'],
};

const DIFFICULTIES = ['Easy', 'Medium', 'Hard'];
const QUESTION_COUNTS = [3, 5, 10];

type Question = { q: string; a: string };

const MOCK_QUESTIONS: Record<string, Question[]> = {
  'Arrays & Linked Lists': [
    { q: 'What is the time complexity of accessing an element in an array by index?', a: 'O(1) — arrays support constant-time random access via index.' },
    { q: 'What is the main advantage of a linked list over an array?', a: 'Dynamic size — linked lists can grow or shrink at runtime without reallocation.' },
    { q: 'How do you detect a cycle in a linked list?', a: "Use Floyd's cycle detection algorithm (slow/fast pointers). If they meet, a cycle exists." },
    { q: 'What is the time complexity of inserting at the head of a singly linked list?', a: 'O(1) — just update the head pointer.' },
    { q: 'What is the difference between a stack and a queue?', a: 'Stack is LIFO (Last In First Out); Queue is FIFO (First In First Out).' },
    { q: 'How do you reverse a singly linked list in-place?', a: 'Iterate through the list, reversing each next pointer. Track prev, curr, and next pointers.' },
    { q: 'What is the space complexity of a linked list with n elements?', a: 'O(n) — each node stores data and a pointer.' },
    { q: 'What is a doubly linked list?', a: 'A linked list where each node has pointers to both the next and previous nodes.' },
    { q: 'When would you prefer an array over a linked list?', a: 'When you need fast random access or cache-friendly sequential traversal.' },
    { q: 'What is the time complexity of searching for an element in an unsorted linked list?', a: 'O(n) — you must traverse the list sequentially.' },
  ],
  'Trees & Graphs': [
    { q: 'What is the difference between a tree and a graph?', a: 'A tree is a connected acyclic graph with n nodes and n-1 edges. Graphs can have cycles.' },
    { q: 'What is the time complexity of BFS and DFS?', a: 'Both are O(V + E) where V is vertices and E is edges.' },
    { q: 'What is a balanced binary search tree?', a: 'A BST where the height difference between left and right subtrees is at most 1 for every node.' },
    { q: 'What is an in-order traversal of a BST?', a: 'Left → Root → Right. For a BST, this produces elements in sorted order.' },
    { q: 'What is Dijkstra\'s algorithm used for?', a: 'Finding the shortest path from a source node to all other nodes in a weighted graph.' },
    { q: 'What is the height of a complete binary tree with n nodes?', a: 'O(log n).' },
    { q: 'What is a heap?', a: 'A complete binary tree satisfying the heap property: parent ≥ children (max-heap) or parent ≤ children (min-heap).' },
    { q: 'What is topological sorting?', a: 'A linear ordering of vertices in a DAG such that for every edge u→v, u comes before v.' },
    { q: 'What is the difference between DFS and BFS?', a: 'DFS uses a stack and explores depth-first; BFS uses a queue and explores level by level.' },
    { q: 'What is a spanning tree?', a: 'A subgraph that includes all vertices of the graph with minimum edges and no cycles.' },
  ],
  'Mitosis & Meiosis': [
    { q: 'What is the main difference between mitosis and meiosis?', a: 'Mitosis produces 2 identical diploid cells; meiosis produces 4 genetically unique haploid cells.' },
    { q: 'During which phase do chromosomes line up at the cell equator?', a: 'Metaphase.' },
    { q: 'What is crossing over and when does it occur?', a: 'Exchange of genetic material between homologous chromosomes; occurs during Prophase I of meiosis.' },
    { q: 'How many chromosomes does a human haploid cell have?', a: '23 chromosomes.' },
    { q: 'What is the purpose of meiosis in sexual reproduction?', a: 'To produce gametes with half the chromosome number, maintaining the species chromosome count after fertilisation.' },
  ],
  'Eigenvalues & Eigenvectors': [
    { q: 'What is an eigenvector?', a: 'A non-zero vector v such that Av = λv for some scalar λ (the eigenvalue).' },
    { q: 'How do you find eigenvalues of a matrix A?', a: 'Solve the characteristic equation det(A - λI) = 0.' },
    { q: 'What does it mean if a matrix has a zero eigenvalue?', a: 'The matrix is singular (non-invertible) and its determinant is 0.' },
    { q: 'What is the geometric multiplicity of an eigenvalue?', a: 'The dimension of the eigenspace (null space of A - λI).' },
    { q: 'When is a matrix diagonalisable?', a: 'When it has n linearly independent eigenvectors (i.e. algebraic multiplicity equals geometric multiplicity for all eigenvalues).' },
  ],
};

function getMockQuestions(topic: string, count: number, difficulty: string): Question[] {
  const pool = MOCK_QUESTIONS[topic] ?? [
    { q: `Explain a key concept in ${topic}.`, a: `A core principle of ${topic} involves understanding the fundamental relationships between its components.` },
    { q: `What is the most important formula or rule in ${topic}?`, a: `The foundational rule in ${topic} defines how elements interact under standard conditions.` },
    { q: `Give an example application of ${topic}.`, a: `${topic} is applied in real-world scenarios to solve problems efficiently and accurately.` },
  ];

  // Shuffle deterministically based on difficulty for variety
  const offset = difficulty === 'Easy' ? 0 : difficulty === 'Medium' ? 2 : 4;
  const rotated = [...pool.slice(offset), ...pool.slice(0, offset)];
  return rotated.slice(0, Math.min(count, rotated.length));
}

export default function PracticePage() {
  const [selectedClass, setSelectedClass] = useState(CLASSES[0]);
  const [selectedTopic, setSelectedTopic] = useState(TOPICS[CLASSES[0]][0]);
  const [difficulty, setDifficulty] = useState('Medium');
  const [count, setCount] = useState(5);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [revealed, setRevealed] = useState<Set<number>>(new Set());
  const [allRevealed, setAllRevealed] = useState(false);
  const [generating, setGenerating] = useState(false);

  const handleClassChange = (cls: string) => {
    setSelectedClass(cls);
    setSelectedTopic(TOPICS[cls][0]);
    setQuestions([]);
    setRevealed(new Set());
    setAllRevealed(false);
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setRevealed(new Set());
    setAllRevealed(false);
    // Simulate network delay
    await new Promise((r) => setTimeout(r, 900));
    setQuestions(getMockQuestions(selectedTopic, count, difficulty));
    setGenerating(false);
  };

  const toggleReveal = (i: number) => {
    setRevealed((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  };

  const handleShowAll = () => {
    if (allRevealed) {
      setRevealed(new Set());
      setAllRevealed(false);
    } else {
      setRevealed(new Set(questions.map((_, i) => i)));
      setAllRevealed(true);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="pt-3 pb-12 px-2 max-w-[860px] mx-auto w-full"
    >
      {/* Header */}
      <header className="mb-8 pl-2">
        <h1 className="text-[28px] font-extrabold tracking-tight text-white mb-2 leading-none">
          Practice Generator
        </h1>
        <p className="text-slate-400 text-xs font-semibold tracking-wide">
          Select a class, topic, and difficulty — then generate a practice set
        </p>
      </header>

      {/* Config card */}
      <div className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] p-6 mb-6 shadow-[0_10px_40px_rgba(0,0,0,0.3)]">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {/* Class */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2 block">Class</label>
            <div className="relative">
              <select
                value={selectedClass}
                onChange={(e) => handleClassChange(e.target.value)}
                className="w-full appearance-none bg-black/30 border border-white/10 rounded-xl py-3 pl-4 pr-10 text-sm text-white focus:outline-none focus:ring-1 focus:ring-[#00F5D4] focus:border-[#00F5D4] transition-all cursor-pointer"
              >
                {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
          </div>

          {/* Topic */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2 block">Topic</label>
            <div className="relative">
              <select
                value={selectedTopic}
                onChange={(e) => { setSelectedTopic(e.target.value); setQuestions([]); }}
                className="w-full appearance-none bg-black/30 border border-white/10 rounded-xl py-3 pl-4 pr-10 text-sm text-white focus:outline-none focus:ring-1 focus:ring-[#00F5D4] focus:border-[#00F5D4] transition-all cursor-pointer"
              >
                {TOPICS[selectedClass].map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
          </div>

          {/* Difficulty */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2 block">Difficulty</label>
            <div className="flex gap-2">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all border ${
                    difficulty === d
                      ? 'border-[#00F5D4]/50 bg-[#00F5D4]/10 text-[#00F5D4]'
                      : 'border-white/10 bg-black/20 text-slate-400 hover:text-white hover:border-white/20'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* # Questions */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2 block">Questions</label>
            <div className="flex gap-2">
              {QUESTION_COUNTS.map((n) => (
                <button
                  key={n}
                  onClick={() => setCount(n)}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all border ${
                    count === n
                      ? 'border-[#6D4AFF]/50 bg-[#6D4AFF]/10 text-[#a78bfa]'
                      : 'border-white/10 bg-black/20 text-slate-400 hover:text-white hover:border-white/20'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating}
          className="w-full py-3.5 rounded-xl font-extrabold text-sm text-[#0B0F2A] flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed shadow-[0_4px_20px_rgba(109,74,255,0.3)]"
          style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
        >
          {generating ? (
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Generating...
            </span>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Generate Practice Set
            </>
          )}
        </button>
      </div>

      {/* Questions */}
      <AnimatePresence>
        {questions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            {/* Show all answers toggle */}
            <div className="flex items-center justify-between mb-4 pl-1">
              <p className="text-slate-400 text-xs font-semibold tracking-wide">
                {questions.length} question{questions.length !== 1 ? 's' : ''} · {selectedTopic} · {difficulty}
              </p>
              <button
                onClick={handleShowAll}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-all"
              >
                {allRevealed ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                {allRevealed ? 'Hide all answers' : 'Show all answers'}
              </button>
            </div>

            <div className="flex flex-col gap-3">
              {questions.map((q, i) => (
                <motion.div
                  key={`${selectedTopic}-${i}`}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.06 }}
                  className="bg-[#141B3A]/50 backdrop-blur-xl border border-white/5 rounded-[1.25rem] overflow-hidden"
                >
                  {/* Question row */}
                  <button
                    onClick={() => toggleReveal(i)}
                    className="w-full flex items-start gap-4 p-5 text-left hover:bg-white/[0.02] transition-colors group"
                  >
                    <span
                      className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-xs font-extrabold text-[#0B0F2A] mt-0.5"
                      style={{ background: 'linear-gradient(135deg, #6D4AFF, #00F5D4)' }}
                    >
                      {i + 1}
                    </span>
                    <p className="flex-1 text-sm font-semibold text-white leading-relaxed">{q.q}</p>
                    <span className={`shrink-0 mt-0.5 transition-transform duration-200 ${revealed.has(i) ? 'rotate-180' : ''}`}>
                      <ChevronDown className="w-4 h-4 text-slate-400 group-hover:text-white" />
                    </span>
                  </button>

                  {/* Answer reveal */}
                  <AnimatePresence>
                    {revealed.has(i) && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25 }}
                        className="overflow-hidden"
                      >
                        <div className="px-5 pb-5 pt-0 ml-11 border-t border-white/5">
                          <p className="text-[11px] font-bold uppercase tracking-widest text-[#00F5D4] mb-2 mt-3">Answer</p>
                          <p className="text-sm text-slate-300 leading-relaxed">{q.a}</p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
